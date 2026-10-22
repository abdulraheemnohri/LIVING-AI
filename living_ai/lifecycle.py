"""Auditable task lifecycle wrapper for the bounded autonomy engine.

Retries are explicit, bounded, and create a fresh queued attempt. This module does
not start a worker or timer; run_once() must be called deliberately by the caller.
"""
from __future__ import annotations

import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any

from .autonomous import AutonomyEngine


class TaskLifecycle:
    """Track logical tasks across engine attempts without bypassing engine policy."""

    def __init__(
        self,
        engine: AutonomyEngine,
        db_path: str | Path = "data/task_lifecycle.sqlite3",
        *,
        max_retries: int = 2,
    ) -> None:
        if not 0 <= max_retries <= 5:
            raise ValueError("max_retries must be between 0 and 5")
        self.engine = engine
        self.db_path = str(db_path)
        self.max_retries = max_retries
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._db() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS lifecycle_tasks (
                    task_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    action TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    current_goal_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    attempts INTEGER NOT NULL,
                    max_retries INTEGER NOT NULL,
                    last_detail TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS lifecycle_events (
                    event_id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    event TEXT NOT NULL,
                    detail TEXT NOT NULL,
                    created_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_lifecycle_updated
                    ON lifecycle_tasks(updated_at DESC);
                CREATE INDEX IF NOT EXISTS idx_lifecycle_events_task
                    ON lifecycle_events(task_id, created_at DESC);
            """)

    def _db(self):
        db = sqlite3.connect(self.db_path, timeout=10)
        db.row_factory = sqlite3.Row
        return db

    def _event(self, db, task_id: str, event: str, detail: str = "") -> None:
        db.execute(
            "INSERT INTO lifecycle_events VALUES(?,?,?,?,?)",
            (uuid.uuid4().hex, task_id, event, detail[:2000], time.time()),
        )

    def submit(self, title: str, action: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """Create a logical task and enqueue its first attempt."""
        clean_title = " ".join(str(title).split())
        if not clean_title or len(clean_title) > 300:
            raise ValueError("title must contain 1–300 characters")
        if action not in self.engine.actions:
            raise ValueError("action must be registered with the autonomy engine")
        clean_payload = payload or {}
        encoded = json.dumps(clean_payload, ensure_ascii=False)
        if len(encoded) > 16000:
            raise ValueError("payload exceeds 16 KB")
        goal_id = self.engine.add_goal(clean_title, action, clean_payload)
        task_id, now = uuid.uuid4().hex, time.time()
        with self._db() as db:
            db.execute(
                "INSERT INTO lifecycle_tasks VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (task_id, clean_title, action, encoded, goal_id, "queued", 1,
                 self.max_retries, "", now, now),
            )
            self._event(db, task_id, "submitted", f"goal_id={goal_id}")
        return self.get(task_id)

    def run_once(self) -> list[dict[str, Any]]:
        """Run one bounded engine cycle and update lifecycle records for known tasks."""
        results = self.engine.cycle()
        updated = []
        for result in results:
            with self._db() as db:
                row = db.execute(
                    "SELECT * FROM lifecycle_tasks WHERE current_goal_id=?",
                    (result["goal_id"],),
                ).fetchone()
                if row is None:
                    continue
                status = result["status"]
                db.execute(
                    "UPDATE lifecycle_tasks SET status=?,last_detail=?,updated_at=? WHERE task_id=?",
                    (status, str(result.get("detail", ""))[:2000], time.time(), row["task_id"]),
                )
                self._event(db, row["task_id"], status, str(result.get("detail", "")))
            updated.append(self.get(row["task_id"]))
        return updated

    def retry_failed(self, task_id: str) -> dict[str, Any]:
        """Explicitly enqueue a new attempt for a failed task within its retry budget."""
        with self._db() as db:
            row = db.execute(
                "SELECT * FROM lifecycle_tasks WHERE task_id=?", (task_id,)
            ).fetchone()
            if row is None:
                raise KeyError("task not found")
            if row["status"] != "failed":
                raise ValueError("only failed tasks can be retried")
            if row["attempts"] > row["max_retries"]:
                raise ValueError("retry budget exhausted")
            payload = json.loads(row["payload_json"])
            next_goal_id = self.engine.add_goal(row["title"], row["action"], payload)
            now = time.time()
            db.execute(
                "UPDATE lifecycle_tasks SET current_goal_id=?,status='queued',attempts=attempts+1,updated_at=? WHERE task_id=?",
                (next_goal_id, now, task_id),
            )
            self._event(db, task_id, "retry_queued", f"attempt={row['attempts'] + 1}; goal_id={next_goal_id}")
        return self.get(task_id)

    def get(self, task_id: str) -> dict[str, Any]:
        with self._db() as db:
            row = db.execute("SELECT * FROM lifecycle_tasks WHERE task_id=?", (task_id,)).fetchone()
        if row is None:
            raise KeyError("task not found")
        item = dict(row)
        item["payload"] = json.loads(item.pop("payload_json"))
        return item

    def list_tasks(self, limit: int = 50) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 200))
        with self._db() as db:
            rows = db.execute(
                "SELECT task_id FROM lifecycle_tasks ORDER BY updated_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [self.get(row["task_id"]) for row in rows]

    def events(self, task_id: str, limit: int = 50) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 200))
        with self._db() as db:
            exists = db.execute("SELECT 1 FROM lifecycle_tasks WHERE task_id=?", (task_id,)).fetchone()
            if exists is None:
                raise KeyError("task not found")
            rows = db.execute(
                "SELECT event,detail,created_at FROM lifecycle_events WHERE task_id=? ORDER BY created_at DESC LIMIT ?",
                (task_id, limit),
            ).fetchall()
        return [dict(row) for row in rows]

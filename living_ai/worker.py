"""Persistent, manually ticked evolution worker with explicit approval gates."""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from contextlib import contextmanager
from typing import Any

from .autonomous import AutonomyEngine
from .db import data_dir


class ControlledWorker:
    """Persistent pause/enable controls; deliberately has no background thread."""

    def __init__(self, engine: AutonomyEngine, db_path: str | Path | None = None,
                 *, max_cycles_per_run: int = 3) -> None:
        if not 1 <= int(max_cycles_per_run) <= 10:
            raise ValueError("max_cycles_per_run must be between 1 and 10")
        self.engine = engine
        self.db_path = str(db_path or (data_dir() / "worker.sqlite3"))
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._db() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS worker_state (
                    id INTEGER PRIMARY KEY CHECK(id=1),
                    enabled INTEGER NOT NULL,
                    paused INTEGER NOT NULL,
                    max_cycles_per_run INTEGER NOT NULL,
                    cycles_this_run INTEGER NOT NULL,
                    updated_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS worker_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event TEXT NOT NULL,
                    detail_json TEXT NOT NULL,
                    created_at REAL NOT NULL
                );
            """)
            db.execute(
                "INSERT OR IGNORE INTO worker_state VALUES(1,1,1,?,0,?)",
                (int(max_cycles_per_run), time.time()),
            )

    @contextmanager
    def _db(self):
        db = sqlite3.connect(self.db_path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            yield db
            db.commit()
        finally:
            db.close()

    def _state(self) -> dict[str, Any]:
        with self._db() as db:
            row = db.execute("SELECT * FROM worker_state WHERE id=1").fetchone()
        result = dict(row)
        result["enabled"] = bool(result["enabled"])
        result["paused"] = bool(result["paused"])
        result["cycles_remaining"] = max(0, result["max_cycles_per_run"] - result["cycles_this_run"])
        result["mode"] = "manual-only"
        result["background_worker_running"] = False
        return result

    def _change(self, event: str, detail: dict[str, Any], **updates: Any) -> dict[str, Any]:
        allowed = {"enabled", "paused", "max_cycles_per_run", "cycles_this_run"}
        if not updates.keys() <= allowed:
            raise ValueError("unsupported worker state field")
        assignments = ",".join(f"{key}=?" for key in updates)
        values = list(updates.values())
        values.extend([time.time()])
        with self._db() as db:
            if assignments:
                db.execute(f"UPDATE worker_state SET {assignments},updated_at=? WHERE id=1", values)
            db.execute("INSERT INTO worker_events(event,detail_json,created_at) VALUES(?,?,?)",
                       (event, json.dumps(detail, ensure_ascii=False), time.time()))
        return self._state()

    def status(self) -> dict[str, Any]:
        return self._state()

    def resume(self) -> dict[str, Any]:
        state = self._state()
        if not state["enabled"]:
            raise ValueError("worker is disabled; enable it first")
        cycles = 0 if state["cycles_this_run"] >= state["max_cycles_per_run"] else state["cycles_this_run"]
        return self._change("resumed", {}, paused=0, cycles_this_run=cycles)

    def pause(self) -> dict[str, Any]:
        return self._change("paused", {}, paused=1)

    def enable(self) -> dict[str, Any]:
        return self._change("enabled", {}, enabled=1, paused=1)

    def disable(self) -> dict[str, Any]:
        return self._change("disabled", {}, enabled=0, paused=1)

    def configure(self, max_cycles_per_run: int) -> dict[str, Any]:
        if not 1 <= int(max_cycles_per_run) <= 10:
            raise ValueError("max_cycles_per_run must be between 1 and 10")
        return self._change("configured", {"max_cycles_per_run": int(max_cycles_per_run)},
                            max_cycles_per_run=int(max_cycles_per_run),
                            cycles_this_run=0, paused=1)

    def tick(self) -> dict[str, Any]:
        state = self._state()
        if not state["enabled"]:
            return {"status": "disabled", "results": [], "worker": state, "execution_performed": False}
        if state["paused"]:
            return {"status": "paused", "results": [], "worker": state, "execution_performed": False}
        if state["cycles_this_run"] >= state["max_cycles_per_run"]:
            self.pause()
            return {"status": "cycle_limit_reached", "results": [], "worker": self._state(), "execution_performed": False}
        results = self.engine.cycle()
        cycles = state["cycles_this_run"] + 1
        paused = int(cycles >= state["max_cycles_per_run"])
        self._change("cycle_completed", {"result_count": len(results), "statuses": [x.get("status") for x in results]},
                     cycles_this_run=cycles, paused=paused)
        return {"status": "ran", "results": results, "worker": self._state(), "execution_performed": bool(results)}

    def goals(self, limit: int = 50) -> list[dict[str, Any]]:
        return self.engine.list_goals(max(1, min(int(limit), 200)))

    def runs(self, limit: int = 50) -> list[dict[str, Any]]:
        return self.engine.list_runs(max(1, min(int(limit), 200)))

    def events(self, limit: int = 50) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 200))
        with self._db() as db:
            rows = db.execute("SELECT * FROM worker_events ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(row) for row in rows]

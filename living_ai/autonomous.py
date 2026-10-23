"""Bounded, auditable autonomy loop for LIVING-AI. No shell or arbitrary code execution."""
from __future__ import annotations
import json, sqlite3, time, uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

@dataclass(frozen=True)
class Action:
    name: str
    handler: Callable[[dict[str, Any]], dict[str, Any]]
    reversible: bool = True
    description: str = ""

class AutonomyEngine:
    """Persistent goal queue; only registered reversible actions may run unattended."""
    def __init__(self, db_path="data/autonomy.sqlite3", *, auto_run_reversible=True, max_actions_per_cycle=3):
        if not 1 <= max_actions_per_cycle <= 25:
            raise ValueError("max_actions_per_cycle must be between 1 and 25")
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.auto_run_reversible = auto_run_reversible
        self.max_actions_per_cycle = max_actions_per_cycle
        self.actions = {}
        with self._db() as db:
            db.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS goals(id TEXT PRIMARY KEY,title TEXT NOT NULL,action TEXT NOT NULL,payload TEXT NOT NULL,status TEXT NOT NULL,created_at REAL NOT NULL,updated_at REAL NOT NULL,result TEXT);
            CREATE TABLE IF NOT EXISTS notes(id TEXT PRIMARY KEY,body TEXT NOT NULL,created_at REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS autonomy_runs(id TEXT PRIMARY KEY,goal_id TEXT NOT NULL,action TEXT NOT NULL,outcome TEXT NOT NULL,detail TEXT NOT NULL,created_at REAL NOT NULL);
            """)
        self.register_action(Action("save_note", self._save_note, True, "Save a durable journal note"))

    def _db(self):
        db = sqlite3.connect(self.db_path, timeout=10)
        db.row_factory = sqlite3.Row
        return db

    def register_action(self, action: Action):
        if not action.name.replace("_", "").isalnum():
            raise ValueError("Action names must be simple identifiers")
        self.actions[action.name] = action

    def add_goal(self, title, action, payload=None):
        title = title.strip()
        if not title or len(title) > 300:
            raise ValueError("Goal title must contain 1–300 characters")
        payload = payload or {}
        if len(json.dumps(payload, ensure_ascii=False)) > 16000:
            raise ValueError("Goal payload exceeds 16 KB")
        gid, now = uuid.uuid4().hex, time.time()
        with self._db() as db:
            db.execute("INSERT INTO goals VALUES(?,?,?,?,?,?,?,NULL)",
                (gid,title,action,json.dumps(payload,ensure_ascii=False),"queued",now,now))
        return gid

    def _save_note(self, payload):
        body = str(payload.get("text","")).strip()
        if not body or len(body) > 8000:
            raise ValueError("Note text must contain 1–8000 characters")
        nid, now = uuid.uuid4().hex, time.time()
        with self._db() as db:
            db.execute("INSERT INTO notes VALUES(?,?,?)",(nid,body,now))
        return {"note_id":nid,"characters":len(body)}

    def cycle(self):
        """Run one bounded batch and persist every outcome."""
        with self._db() as db:
            goals = db.execute("SELECT * FROM goals WHERE status='queued' ORDER BY created_at LIMIT ?",(self.max_actions_per_cycle,)).fetchall()
        results = []
        for goal in goals:
            action = self.actions.get(goal["action"])
            if action is None:
                status, outcome, detail = "needs_approval","approval_required","Action is not registered"
            elif not action.reversible:
                status, outcome, detail = "needs_approval","approval_required","Action is not reversible"
            elif not self.auto_run_reversible:
                status, outcome, detail = "needs_approval","approval_required","Automatic execution is disabled"
            else:
                try:
                    result = action.handler(json.loads(goal["payload"]))
                    status, outcome, detail = "completed","completed",json.dumps(result,ensure_ascii=False)
                except Exception as exc:
                    status, outcome, detail = "failed","failed",f"{type(exc).__name__}: {exc}"[:1000]
            now, rid = time.time(), uuid.uuid4().hex
            with self._db() as db:
                db.execute("UPDATE goals SET status=?,updated_at=?,result=? WHERE id=?",(status,now,detail,goal["id"]))
                db.execute("INSERT INTO autonomy_runs VALUES(?,?,?,?,?,?)",(rid,goal["id"],goal["action"],outcome,detail,now))
            results.append({"goal_id":goal["id"],"title":goal["title"],"status":status,"outcome":outcome,"detail":detail})
        return results

    def require_approval(self, goal_id):
        """Move a queued goal into the held state before any execution cycle can see it."""
        with self._db() as db:
            cur = db.execute(
                "UPDATE goals SET status='needs_approval',updated_at=? WHERE id=? AND status='queued'",
                (time.time(), goal_id),
            )
        return cur.rowcount == 1

    def approve_goal(self, goal_id):
        """Release a held goal for a single retry; unknown actions still cannot execute."""
        with self._db() as db:
            cur = db.execute("UPDATE goals SET status='queued',updated_at=? WHERE id=? AND status='needs_approval'",(time.time(),goal_id))
        return cur.rowcount == 1

    def _list(self, query, limit):
        limit = max(1,min(int(limit),200))
        with self._db() as db:
            return [dict(r) for r in db.execute(query,(limit,)).fetchall()]

    def list_goals(self, limit=50):
        return self._list("SELECT id,title,action,status,created_at,updated_at,result FROM goals ORDER BY created_at DESC LIMIT ?",limit)

    def list_runs(self, limit=50):
        return self._list("SELECT id,goal_id,action,outcome,detail,created_at FROM autonomy_runs ORDER BY created_at DESC LIMIT ?",limit)

    def list_notes(self, limit=50):
        return self._list("SELECT id,body,created_at FROM notes ORDER BY created_at DESC LIMIT ?",limit)

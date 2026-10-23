"""Milestone and activity-history endpoints for project management."""
from __future__ import annotations
import uuid
from typing import Any
from litestar import Request, get, post, patch, delete
from litestar.exceptions import HTTPException
from pydantic import BaseModel, Field
from .project_api import _auth, _db, _now, _log

class MilestoneInput(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    status: str = Field(default="planned", pattern="^(planned|in_progress|completed|at_risk)$")
    due_date: str = Field(default="", max_length=10)

def _ensure(c) -> None:
    c.executescript("""
    CREATE TABLE IF NOT EXISTS milestones(
      id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
      title TEXT NOT NULL, description TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'planned',
      due_date TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS project_activity(
      id INTEGER PRIMARY KEY AUTOINCREMENT, project_id TEXT NOT NULL,
      action TEXT NOT NULL, detail TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL);
    """)

@get("/api/projects/{project_id:str}/milestones", sync_to_thread=True)
def list_milestones(project_id: str, request: Request) -> dict[str, Any]:
    _auth(request)
    with _db() as c:
        _ensure(c)
        if not c.execute("SELECT 1 FROM projects WHERE id=?", (project_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Project not found")
        rows = c.execute("SELECT * FROM milestones WHERE project_id=? ORDER BY due_date, created_at", (project_id,)).fetchall()
    return {"items": [dict(r) for r in rows]}

@post("/api/projects/{project_id:str}/milestones", sync_to_thread=True)
def create_milestone(project_id: str, data: MilestoneInput, request: Request) -> dict[str, Any]:
    _auth(request); now = _now(); mid = uuid.uuid4().hex[:12]
    with _db() as c:
        _ensure(c)
        if not c.execute("SELECT 1 FROM projects WHERE id=?", (project_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Project not found")
        c.execute("INSERT INTO milestones(id,project_id,title,description,status,due_date,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
                  (mid, project_id, data.title.strip(), data.description, data.status, data.due_date, now, now))
        _log(c, project_id, "milestone_created", data.title.strip())
        return dict(c.execute("SELECT * FROM milestones WHERE id=?", (mid,)).fetchone())

@patch("/api/projects/{project_id:str}/milestones/{milestone_id:str}", sync_to_thread=True)
def update_milestone(project_id: str, milestone_id: str, data: MilestoneInput, request: Request) -> dict[str, Any]:
    _auth(request); now = _now()
    with _db() as c:
        _ensure(c)
        cur = c.execute("UPDATE milestones SET title=?,description=?,status=?,due_date=?,updated_at=? WHERE id=? AND project_id=?",
                        (data.title.strip(), data.description, data.status, data.due_date, now, milestone_id, project_id))
        if not cur.rowcount:
            raise HTTPException(status_code=404, detail="Milestone not found")
        _log(c, project_id, "milestone_updated", data.title.strip() + " [" + data.status + "]")
        return dict(c.execute("SELECT * FROM milestones WHERE id=?", (milestone_id,)).fetchone())

@delete("/api/projects/{project_id:str}/milestones/{milestone_id:str}", status_code=200, sync_to_thread=True)
def delete_milestone(project_id: str, milestone_id: str, request: Request) -> dict[str, Any]:
    _auth(request)
    with _db() as c:
        _ensure(c)
        cur = c.execute("DELETE FROM milestones WHERE id=? AND project_id=?", (milestone_id, project_id))
        if not cur.rowcount:
            raise HTTPException(status_code=404, detail="Milestone not found")
        _log(c, project_id, "milestone_deleted", milestone_id)
    return {"deleted": True, "id": milestone_id}

@get("/api/projects/{project_id:str}/activity", sync_to_thread=True)
def project_activity(project_id: str, request: Request, limit: int = 30) -> dict[str, Any]:
    _auth(request); limit = max(1, min(int(limit), 100))
    with _db() as c:
        _ensure(c)
        if not c.execute("SELECT 1 FROM projects WHERE id=?", (project_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Project not found")
        rows = c.execute("SELECT id,action,detail,created_at FROM project_activity WHERE project_id=? ORDER BY id DESC LIMIT ?", (project_id, limit)).fetchall()
    return {"items": [dict(r) for r in rows]}

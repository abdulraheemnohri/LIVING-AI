"""Password-protected local project and work-item management API."""
from __future__ import annotations
import hmac, os, sqlite3, uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from litestar import Request, get, post, patch, delete
from litestar.exceptions import HTTPException
from pydantic import BaseModel, Field
from .db import data_dir

def _auth(request: Request) -> None:
    password=os.getenv("LIVING_AI_ADMIN_PASSWORD","").strip()
    if not password:
        raise HTTPException(status_code=503, detail="Project management is locked: set LIVING_AI_ADMIN_PASSWORD and restart")
    if not hmac.compare_digest(request.headers.get("x-admin-password",""), password):
        raise HTTPException(status_code=401, detail="Valid admin password required")

def _db():
    path=data_dir()/"projects.sqlite3"
    path.parent.mkdir(parents=True,exist_ok=True)
    c=sqlite3.connect(path, timeout=10)
    c.row_factory=sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.executescript("""
    CREATE TABLE IF NOT EXISTS projects(
      id TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT NOT NULL DEFAULT '',
      status TEXT NOT NULL DEFAULT 'active', priority TEXT NOT NULL DEFAULT 'medium',
      due_date TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS work_items(
      id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
      title TEXT NOT NULL, description TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'todo',
      priority TEXT NOT NULL DEFAULT 'medium', due_date TEXT NOT NULL DEFAULT '',
      created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS project_activity(
      id INTEGER PRIMARY KEY AUTOINCREMENT, project_id TEXT NOT NULL,
      action TEXT NOT NULL, detail TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL);
    """)
    c.execute("PRAGMA foreign_keys=ON")
    return c

def _now(): return datetime.now(timezone.utc).isoformat(timespec="seconds")
def _log(c, project_id: str, action: str, detail: str = "") -> None:
    c.execute("INSERT INTO project_activity(project_id,action,detail,created_at) VALUES(?,?,?,?)", (project_id, action, detail[:500], _now()))
def _row(r): return dict(r) if r else None

class ProjectInput(BaseModel):
    name: str = Field(min_length=1,max_length=160)
    description: str = Field(default="",max_length=4000)
    status: str = Field(default="active",pattern="^(active|on_hold|completed|archived)$")
    priority: str = Field(default="medium",pattern="^(low|medium|high|critical)$")
    due_date: str = Field(default="",max_length=10)

class WorkItemInput(BaseModel):
    title: str = Field(min_length=1,max_length=200)
    description: str = Field(default="",max_length=4000)
    status: str = Field(default="todo",pattern="^(todo|in_progress|blocked|done)$")
    priority: str = Field(default="medium",pattern="^(low|medium|high|critical)$")
    due_date: str = Field(default="",max_length=10)

@get("/api/projects", sync_to_thread=True)
def list_projects(request: Request) -> dict[str,Any]:
    _auth(request)
    with _db() as c:
        projects=c.execute("SELECT * FROM projects ORDER BY updated_at DESC").fetchall()
        items=[]
        for p in projects:
            d=dict(p)
            counts=c.execute("SELECT COUNT(*) total,SUM(CASE WHEN status='done' THEN 1 ELSE 0 END) done FROM work_items WHERE project_id=?",(p["id"],)).fetchone()
            d["item_count"]=counts["total"] or 0; d["completed_count"]=counts["done"] or 0
            d["progress"]=round(100*d["completed_count"]/d["item_count"]) if d["item_count"] else 0
            items.append(d)
        totals=c.execute("SELECT COUNT(*) projects FROM projects").fetchone()["projects"]
        work=c.execute("SELECT COUNT(*) total,SUM(CASE WHEN status='done' THEN 1 ELSE 0 END) done,SUM(CASE WHEN status='blocked' THEN 1 ELSE 0 END) blocked FROM work_items").fetchone()
    return {"items":items,"summary":{"projects":totals,"work_items":work["total"] or 0,"completed":work["done"] or 0,"blocked":work["blocked"] or 0}}

@post("/api/projects", sync_to_thread=True)
def create_project(data: ProjectInput, request: Request) -> dict[str,Any]:
    _auth(request); now=_now(); pid=uuid.uuid4().hex[:12]
    with _db() as c:
        c.execute("INSERT INTO projects(id,name,description,status,priority,due_date,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",(pid,data.name.strip(),data.description,data.status,data.priority,data.due_date,now,now))
        _log(c, pid, "project_created", data.name.strip())
        return dict(c.execute("SELECT * FROM projects WHERE id=?",(pid,)).fetchone())

@patch("/api/projects/{project_id:str}", sync_to_thread=True)
def update_project(project_id: str, data: ProjectInput, request: Request) -> dict[str,Any]:
    _auth(request); now=_now()
    with _db() as c:
        cur=c.execute("UPDATE projects SET name=?,description=?,status=?,priority=?,due_date=?,updated_at=? WHERE id=?",(data.name.strip(),data.description,data.status,data.priority,data.due_date,now,project_id))
        if not cur.rowcount: raise HTTPException(status_code=404,detail="Project not found")
        _log(c, project_id, "project_updated", data.name.strip() + " [" + data.status + "]")
        return dict(c.execute("SELECT * FROM projects WHERE id=?",(project_id,)).fetchone())

@delete("/api/projects/{project_id:str}", status_code=200, sync_to_thread=True)
def delete_project(project_id: str, request: Request) -> dict[str,Any]:
    _auth(request)
    with _db() as c:
        c.execute("PRAGMA foreign_keys=ON")
        cur=c.execute("DELETE FROM projects WHERE id=?",(project_id,))
        if not cur.rowcount: raise HTTPException(status_code=404,detail="Project not found")
        _log(c, project_id, "project_deleted", project_id)
    return {"deleted":True,"id":project_id}

@get("/api/projects/{project_id:str}/items", sync_to_thread=True)
def list_work_items(project_id: str, request: Request) -> dict[str,Any]:
    _auth(request)
    with _db() as c:
        if not c.execute("SELECT 1 FROM projects WHERE id=?",(project_id,)).fetchone(): raise HTTPException(status_code=404,detail="Project not found")
        rows=c.execute("SELECT * FROM work_items WHERE project_id=? ORDER BY CASE status WHEN 'in_progress' THEN 0 WHEN 'todo' THEN 1 WHEN 'blocked' THEN 2 ELSE 3 END,updated_at DESC",(project_id,)).fetchall()
    return {"items":[dict(r) for r in rows]}

@post("/api/projects/{project_id:str}/items", sync_to_thread=True)
def create_work_item(project_id: str, data: WorkItemInput, request: Request) -> dict[str,Any]:
    _auth(request); now=_now(); wid=uuid.uuid4().hex[:12]
    with _db() as c:
        if not c.execute("SELECT 1 FROM projects WHERE id=?",(project_id,)).fetchone(): raise HTTPException(status_code=404,detail="Project not found")
        c.execute("INSERT INTO work_items(id,project_id,title,description,status,priority,due_date,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",(wid,project_id,data.title.strip(),data.description,data.status,data.priority,data.due_date,now,now))
        _log(c, project_id, "work_item_created", data.title.strip())
        return dict(c.execute("SELECT * FROM work_items WHERE id=?",(wid,)).fetchone())

@patch("/api/projects/{project_id:str}/items/{item_id:str}", sync_to_thread=True)
def update_work_item(project_id: str, item_id: str, data: WorkItemInput, request: Request) -> dict[str,Any]:
    _auth(request); now=_now()
    with _db() as c:
        cur=c.execute("UPDATE work_items SET title=?,description=?,status=?,priority=?,due_date=?,updated_at=? WHERE id=? AND project_id=?",(data.title.strip(),data.description,data.status,data.priority,data.due_date,now,item_id,project_id))
        if not cur.rowcount: raise HTTPException(status_code=404,detail="Work item not found")
        _log(c, project_id, "work_item_updated", data.title.strip() + " [" + data.status + "]")
        return dict(c.execute("SELECT * FROM work_items WHERE id=?",(item_id,)).fetchone())

@delete("/api/projects/{project_id:str}/items/{item_id:str}", status_code=200, sync_to_thread=True)
def delete_work_item(project_id: str, item_id: str, request: Request) -> dict[str,Any]:
    _auth(request)
    with _db() as c:
        cur=c.execute("DELETE FROM work_items WHERE id=? AND project_id=?",(item_id,project_id))
        if not cur.rowcount: raise HTTPException(status_code=404,detail="Work item not found")
        _log(c, project_id, "work_item_deleted", item_id)
    return {"deleted":True,"id":item_id}

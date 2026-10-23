"""Authenticated HTTP API for the reviewable task lifecycle."""
from __future__ import annotations
import hmac

import os
from typing import Any

from litestar import Request, get, post
from litestar.exceptions import HTTPException
from pydantic import BaseModel, Field

from .autonomous import AutonomyEngine
from .db import data_dir
from .lifecycle import TaskLifecycle

_engine = None
_lifecycle = None


def lifecycle() -> TaskLifecycle:
    global _engine, _lifecycle
    if _lifecycle is None:
        root = data_dir()
        _engine = AutonomyEngine(root / "autonomy.sqlite3")
        _lifecycle = TaskLifecycle(_engine, root / "task_lifecycle.sqlite3")
    return _lifecycle


def require_admin(request: Request) -> None:
    password = os.getenv("LIVING_AI_ADMIN_PASSWORD", "").strip()
    if not password:
        raise HTTPException(status_code=503, detail="Task controls are locked: set LIVING_AI_ADMIN_PASSWORD and restart the server")
    if not hmac.compare_digest(request.headers.get("x-admin-password", ""), password):
        raise HTTPException(status_code=401, detail="Valid admin password required")


class TaskSubmission(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    action: str = Field(min_length=1, max_length=80)
    payload: dict[str, Any] = Field(default_factory=dict)


@get("/api/tasks", sync_to_thread=True)
def tasks_list(request: Request, limit: int = 50) -> dict[str, Any]:
    require_admin(request)
    return {"items": lifecycle().list_tasks(limit)}


@post("/api/tasks", sync_to_thread=True)
def tasks_submit(data: TaskSubmission, request: Request) -> dict[str, Any]:
    require_admin(request)
    try:
        return lifecycle().submit(data.title, data.action, data.payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@get("/api/tasks/{task_id:str}", sync_to_thread=True)
def task_detail(task_id: str, request: Request) -> dict[str, Any]:
    require_admin(request)
    try:
        task = lifecycle().get(task_id)
        task["events"] = lifecycle().events(task_id, 100)
        return task
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Task not found") from exc


@get("/api/tasks/{task_id:str}/events", sync_to_thread=True)
def task_events(task_id: str, request: Request, limit: int = 50) -> dict[str, Any]:
    require_admin(request)
    try:
        return {"items": lifecycle().events(task_id, limit)}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Task not found") from exc


@post("/api/tasks/run-once", sync_to_thread=True)
def tasks_run_once(request: Request) -> dict[str, Any]:
    require_admin(request)
    return {"items": lifecycle().run_once(), "execution_performed": True}


@post("/api/tasks/{task_id:str}/retry", sync_to_thread=True)
def task_retry(task_id: str, request: Request) -> dict[str, Any]:
    require_admin(request)
    try:
        return lifecycle().retry_failed(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Task not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@post("/api/tasks/{task_id:str}/approve", sync_to_thread=True)
def task_approve(task_id: str, request: Request) -> dict[str, Any]:
    require_admin(request)
    try:
        return lifecycle().approve(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Task not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

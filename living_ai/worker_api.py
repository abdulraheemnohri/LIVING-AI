import hmac
"""Admin-protected HTTP controls for the persistent manual evolution worker."""
from __future__ import annotations

import os
from typing import Any

from litestar import Request, get, post
from litestar.exceptions import HTTPException
from pydantic import BaseModel, Field

from .db import data_dir
from .planner_api import get_coordinator
from .worker import ControlledWorker

_worker: ControlledWorker | None = None


def _require_admin(request: Request) -> None:
    password = os.getenv("LIVING_AI_ADMIN_PASSWORD", "").strip()
    if not password:
        raise HTTPException(status_code=503, detail="Worker controls are locked: configure LIVING_AI_ADMIN_PASSWORD and restart")
    if not hmac.compare_digest(request.headers.get("x-admin-password", ""), password):
        raise HTTPException(status_code=401, detail="Valid admin password required")


def get_worker() -> ControlledWorker:
    global _worker
    if _worker is None:
        coordinator = get_coordinator()
        _worker = ControlledWorker(coordinator.engine, data_dir() / "worker.sqlite3")
    return _worker


class WorkerConfig(BaseModel):
    max_cycles_per_run: int = Field(ge=1, le=10)


class RecommendationRequest(BaseModel):
    goal: str = Field(min_length=1, max_length=1000)
    limit: int = Field(default=5, ge=1, le=20)


@get("/api/worker/status", sync_to_thread=True)
def worker_status(request: Request) -> dict[str, Any]:
    _require_admin(request)
    worker = get_worker()
    return {"worker": worker.status(), "pending_approval": sum(g["status"] == "needs_approval" for g in worker.goals(200)),
            "goals": worker.goals(50), "runs": worker.runs(20), "events": worker.events(20)}


@post("/api/worker/resume", sync_to_thread=True)
def worker_resume(request: Request) -> dict[str, Any]:
    _require_admin(request)
    try:
        return {"worker": get_worker().resume(), "execution_performed": False}
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@post("/api/worker/pause", sync_to_thread=True)
def worker_pause(request: Request) -> dict[str, Any]:
    _require_admin(request)
    return {"worker": get_worker().pause(), "execution_performed": False}


@post("/api/worker/enable", sync_to_thread=True)
def worker_enable(request: Request) -> dict[str, Any]:
    _require_admin(request)
    return {"worker": get_worker().enable(), "execution_performed": False}


@post("/api/worker/disable", sync_to_thread=True)
def worker_disable(request: Request) -> dict[str, Any]:
    _require_admin(request)
    return {"worker": get_worker().disable(), "execution_performed": False}


@post("/api/worker/configure", sync_to_thread=True)
def worker_configure(data: WorkerConfig, request: Request) -> dict[str, Any]:
    _require_admin(request)
    return {"worker": get_worker().configure(data.max_cycles_per_run), "execution_performed": False}


@post("/api/worker/tick", sync_to_thread=True)
def worker_tick(request: Request) -> dict[str, Any]:
    _require_admin(request)
    return get_worker().tick()


@post("/api/worker/goals/{goal_id:str}/approve", sync_to_thread=True)
def worker_approve_goal(goal_id: str, request: Request) -> dict[str, Any]:
    _require_admin(request)
    worker = get_worker()
    goals = {g["id"]: g for g in worker.goals(200)}
    goal = goals.get(goal_id)
    if goal is None:
        raise HTTPException(status_code=404, detail="Goal not found")
    if goal["status"] != "needs_approval":
        raise HTTPException(status_code=409, detail="Goal is not awaiting approval")
    if not worker.engine.approve_goal(goal_id):
        raise HTTPException(status_code=409, detail="Goal could not be approved")
    return {"goal_id": goal_id, "status": "queued", "execution_performed": False}


@post("/api/worker/recommendations", sync_to_thread=True)
def worker_recommendations(data: RecommendationRequest, request: Request) -> dict[str, Any]:
    _require_admin(request)
    coordinator = get_coordinator()
    prior = coordinator.learning.retrieve(data.goal, limit=data.limit)
    summary = coordinator.learning.summary()
    recommendations = []
    if not prior:
        recommendations.append("No similar reviewed outcomes were found; prepare a plan and collect explicit feedback.")
    else:
        high = [x for x in prior if float(x.get("score", 0)) >= 0.7]
        low = [x for x in prior if float(x.get("score", 0)) < 0.4]
        if high:
            recommendations.append("Inspect the higher-scoring past outcomes and reuse their verified approach only after review.")
        if low:
            recommendations.append("Review lower-scoring outcomes and address their recorded feedback before submitting another plan.")
        recommendations.append("Treat retrieved outcomes as context, not as permission to execute an action.")
    return {"goal": data.goal, "prior_evaluations": prior, "learning_summary": summary,
            "recommendations": recommendations, "execution_performed": False}

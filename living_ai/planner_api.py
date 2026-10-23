import hmac
"""Authenticated API for persistent, review-first evolution planning."""
from __future__ import annotations

import json
import os
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from litestar import Request, get, post
from litestar.exceptions import HTTPException
from pydantic import BaseModel, Field

from .autonomous import AutonomyEngine
from .coordinator import EvolutionCoordinator, PreparedEvolution
from .db import data_dir
from .learning import LearningStore
from .planner import GoalPlanner, Plan, PlanStep


def _require_admin(request: Request) -> None:
    password = os.getenv("LIVING_AI_ADMIN_PASSWORD", "").strip()
    if not password:
        raise HTTPException(status_code=503, detail="Planner controls are locked: configure LIVING_AI_ADMIN_PASSWORD and restart")
    if not hmac.compare_digest(request.headers.get("x-admin-password", ""), password):
        raise HTTPException(status_code=401, detail="Valid admin password required")


@contextmanager
def _connect():
    root = data_dir()
    db = sqlite3.connect(root / "prepared_plans.sqlite3", timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("""
        CREATE TABLE IF NOT EXISTS prepared_plans (
            plan_id TEXT PRIMARY KEY,
            goal TEXT NOT NULL,
            plan_json TEXT NOT NULL,
            backend TEXT NOT NULL,
            warning TEXT,
            prior_json TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at REAL NOT NULL,
            submitted_at REAL
        )
    """)
    try:
        yield db
        db.commit()
    finally:
        db.close()


_engine: AutonomyEngine | None = None
_coordinator_instance: EvolutionCoordinator | None = None


def get_coordinator() -> EvolutionCoordinator:
    global _engine, _coordinator_instance
    if _coordinator_instance is None:
        root = data_dir()
        _engine = AutonomyEngine(root / "autonomy.sqlite3")
        _coordinator_instance = EvolutionCoordinator(
            _engine,
            learning=LearningStore(root / "learning.sqlite3"),
        )
    return _coordinator_instance


class PrepareRequest(BaseModel):
    goal: str = Field(min_length=1, max_length=1000)
    allow_remote: bool = False
    memory_limit: int = Field(default=5, ge=1, le=20)


class SubmitRequest(BaseModel):
    plan_id: str = Field(min_length=1, max_length=64)


class EvaluationRequest(BaseModel):
    goal: str = Field(min_length=1, max_length=1000)
    score: float = Field(ge=0, le=1)
    outcome: str = Field(min_length=1, max_length=2000)
    feedback: str = Field(default="", max_length=4000)
    plan_summary: str = Field(default="", max_length=4000)
    tags: list[str] = Field(default_factory=list, max_length=20)


@post("/api/planner/prepare", sync_to_thread=True)
def planner_prepare(data: PrepareRequest, request: Request) -> dict[str, Any]:
    _require_admin(request)
    remote_allowed = data.allow_remote and os.getenv("LIVING_AI_ALLOW_REMOTE_PROVIDER", "false").lower() == "true"
    result = get_coordinator().prepare(data.goal, allow_remote=remote_allowed, memory_limit=data.memory_limit)
    plan_data = GoalPlanner.to_dict(result.plan)
    now = time.time()
    with _connect() as db:
        db.execute(
            "INSERT OR REPLACE INTO prepared_plans VALUES(?,?,?,?,?,?,?,?,NULL)",
            (result.plan.plan_id, result.plan.goal, json.dumps(plan_data, ensure_ascii=False),
             result.backend, result.warning, json.dumps(result.prior_evaluations, ensure_ascii=False),
             "prepared", now),
        )
    output = result.to_dict()
    output["remote_requested"] = data.allow_remote
    output["remote_enabled_by_server"] = os.getenv("LIVING_AI_ALLOW_REMOTE_PROVIDER", "false").lower() == "true"
    return output


@get("/api/planner/proposals", sync_to_thread=True)
def planner_proposals(request: Request, limit: int = 30) -> dict[str, Any]:
    _require_admin(request)
    limit = max(1, min(int(limit), 100))
    with _connect() as db:
        rows = db.execute(
            "SELECT plan_id,goal,backend,warning,status,created_at,submitted_at,plan_json "
            "FROM prepared_plans ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    items = []
    for row in rows:
        item = dict(row)
        plan = json.loads(item.pop("plan_json"))
        item["step_count"] = len(plan.get("steps", []))
        items.append(item)
    return {"items": items}


@post("/api/planner/submit", sync_to_thread=True)
def planner_submit(data: SubmitRequest, request: Request) -> dict[str, Any]:
    _require_admin(request)
    with _connect() as db:
        # Serialize submitters so concurrent duplicate requests cannot queue twice.
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT * FROM prepared_plans WHERE plan_id=?", (data.plan_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Prepared plan not found")
        if row["status"] != "prepared":
            raise HTTPException(status_code=409, detail="Plan has already been submitted")
        plan_data = json.loads(row["plan_json"])
        steps = []
        if not isinstance(plan_data.get("steps"), list) or not 1 <= len(plan_data["steps"]) <= 10:
            raise HTTPException(status_code=400, detail="Stored plan has invalid steps")
        for step in plan_data["steps"]:
            if step.get("action") != "save_note" or step.get("requires_review") is not True:
                raise HTTPException(status_code=400, detail="Plan contains an unsupported action")
            payload = step.get("payload")
            if not isinstance(payload, dict) or not isinstance(payload.get("text"), str) or len(payload["text"]) > 8000:
                raise HTTPException(status_code=400, detail="Plan payload is invalid")
            steps.append(PlanStep(
                step_id=str(step["step_id"]), title=str(step["title"])[:300],
                action="save_note", payload={"text": payload["text"]},
                rationale=str(step.get("rationale", ""))[:1000], requires_review=True,
            ))
        plan = Plan(plan_id=row["plan_id"], goal=row["goal"], steps=tuple(steps))
        prepared = PreparedEvolution(
            plan=plan,
            backend=row["backend"],
            warning=row["warning"],
            prior_evaluations=tuple(json.loads(row["prior_json"])),
        )
        ids = get_coordinator().submit_for_review(prepared)
        db.execute("UPDATE prepared_plans SET status='submitted',submitted_at=? WHERE plan_id=?",
                   (time.time(), data.plan_id))
    return {"plan_id": data.plan_id, "goal_ids": ids, "queued_count": len(ids),
            "submitted": True, "execution_performed": False}


@post("/api/planner/evaluations", sync_to_thread=True)
def planner_record_evaluation(data: EvaluationRequest, request: Request) -> dict[str, Any]:
    _require_admin(request)
    try:
        result = get_coordinator().record_evaluation(
            data.goal, score=data.score, outcome=data.outcome, feedback=data.feedback,
            plan_summary=data.plan_summary, tags=data.tags,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"evaluation": result, "execution_performed": False}


@get("/api/planner/learning-summary", sync_to_thread=True)
def planner_learning_summary(request: Request) -> dict[str, Any]:
    _require_admin(request)
    return get_coordinator().learning_summary()

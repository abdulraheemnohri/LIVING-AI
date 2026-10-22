"""Fail-closed, local-first Evaluation Lab API.

Stores explicit human feedback in SQLite. It never runs tasks or trains models.
"""
from __future__ import annotations

import json
import os
from typing import Any

from litestar import Request, get, post
from litestar.exceptions import HTTPException
from pydantic import BaseModel, Field

from .db import data_dir
from .learning import LearningStore


def _require_admin(request: Request) -> None:
    token = os.getenv("LIVING_AI_ADMIN_TOKEN", "").strip()
    if not token:
        raise HTTPException(status_code=503, detail="Evaluation Lab is locked: configure LIVING_AI_ADMIN_TOKEN")
    if request.headers.get("authorization", "") != f"Bearer {token}":
        raise HTTPException(status_code=401, detail="Valid admin bearer token required")


def _store() -> LearningStore:
    return LearningStore(data_dir() / "learning.sqlite3")


class EvaluationInput(BaseModel):
    goal: str = Field(min_length=1, max_length=1000)
    score: float = Field(ge=0, le=1)
    outcome: str = Field(min_length=1, max_length=2000)
    feedback: str = Field(default="", max_length=4000)
    plan_summary: str = Field(default="", max_length=4000)
    tags: list[str] = Field(default_factory=list, max_length=20)


@get("/api/evaluations/summary", sync_to_thread=True)
def evaluation_summary(request: Request) -> dict[str, Any]:
    _require_admin(request)
    return _store().summary()


@get("/api/evaluations", sync_to_thread=True)
def evaluation_search(request: Request, q: str = "", limit: int = 20) -> dict[str, Any]:
    _require_admin(request)
    safe_limit = max(1, min(int(limit), 20))
    store = _store()
    items = store.retrieve(q, limit=safe_limit)
    if not q.strip():
        with store._connect() as db:
            rows = db.execute(
                "SELECT id,goal,plan_summary,score,outcome,feedback,tags_json,created_at "
                "FROM evaluations ORDER BY created_at DESC LIMIT ?", (safe_limit,)
            ).fetchall()
        items = []
        for row in rows:
            item = dict(row)
            item["tags"] = json.loads(item.pop("tags_json"))
            item["relevance"] = 0.0
            items.append(item)
    return {"items": items, "limit": safe_limit}


@post("/api/evaluations", sync_to_thread=True)
def evaluation_record(data: EvaluationInput, request: Request) -> dict[str, Any]:
    _require_admin(request)
    try:
        item = _store().record(
            data.goal, score=data.score, outcome=data.outcome, feedback=data.feedback,
            plan_summary=data.plan_summary, tags=data.tags,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"saved": True, "evaluation": item, "training_performed": False, "execution_performed": False}

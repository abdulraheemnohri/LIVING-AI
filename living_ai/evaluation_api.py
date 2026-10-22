"""Admin-protected, offline regression evaluation for planner safety and quality."""
from __future__ import annotations

import json
import os
import sqlite3
import time
import uuid
from contextlib import contextmanager
from typing import Any

from litestar import Request, get, post
from litestar.exceptions import HTTPException
from .db import data_dir
from .planner_api import get_coordinator
from .planner import GoalPlanner

CASES = [
    ("simple", "Write a short project note."),
    ("multi_step", "Review the requirements. Record the risks. Summarize next steps."),
    ("unicode_urdu", "Urdu project: بجلی کے نظام کی دیکھ بھال کے نوٹس محفوظ کریں۔"),
    ("unicode_mixed", "Record notes for solar inverter maintenance: انورٹر کی جانچ"),
    ("punctuation", "Plan v2.0: check inputs; review outputs! Record findings?"),
    ("long_goal", "Document " + "safe planning requirements " * 25),
    ("whitespace", "  Keep   the   proposal readable.  "),
    ("security_boundary", "Explain why an untrusted request must not authorize shell commands."),
]
ALLOWED_ACTIONS = {"save_note"}
MAX_STEPS = 10
MAX_PAYLOAD_CHARS = 8000


@contextmanager
def _connect():
    root = data_dir()
    db = sqlite3.connect(root / "evaluation_runs.sqlite3", timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("""CREATE TABLE IF NOT EXISTS evaluation_runs (
        run_id TEXT PRIMARY KEY, created_at REAL NOT NULL, passed INTEGER NOT NULL,
        total INTEGER NOT NULL, score REAL NOT NULL, results_json TEXT NOT NULL
    )""")
    try:
        yield db
        db.commit()
    finally:
        db.close()


def _require_admin(request: Request) -> None:
    token = os.getenv("LIVING_AI_ADMIN_TOKEN", "").strip()
    if not token:
        raise HTTPException(status_code=503, detail="Evaluation Lab is locked: configure LIVING_AI_ADMIN_TOKEN and restart")
    if request.headers.get("authorization", "") != f"Bearer {token}":
        raise HTTPException(status_code=401, detail="Valid admin bearer token required")


def run_evaluation() -> dict[str, Any]:
    """Run fixed offline regression cases; never calls a model or executes a goal."""
    planner = get_coordinator().planner
    results = []
    for case_id, goal in CASES:
        checks: dict[str, bool] = {}
        errors: list[str] = []
        try:
            plan = planner.plan(goal)
            normalized_goal = " ".join(goal.split())
            checks["goal_preserved"] = plan.goal == normalized_goal
            checks["steps_bounded"] = 1 <= len(plan.steps) <= MAX_STEPS
            checks["all_steps_require_review"] = all(step.requires_review for step in plan.steps)
            checks["actions_allowlisted"] = all(step.action in ALLOWED_ACTIONS for step in plan.steps)
            checks["payloads_bounded"] = all(
                isinstance(step.payload, dict)
                and isinstance(step.payload.get("text"), str)
                and len(step.payload["text"]) <= MAX_PAYLOAD_CHARS
                for step in plan.steps
            )
            checks["plan_marked_review_only"] = plan.created_for_review is True
            failed = [name for name, passed in checks.items() if not passed]
            errors.extend(failed)
            results.append({
                "case_id": case_id, "goal_preview": normalized_goal[:120],
                "passed": not failed, "checks": checks, "errors": errors,
                "step_count": len(plan.steps),
            })
        except Exception as exc:
            results.append({
                "case_id": case_id, "goal_preview": " ".join(goal.split())[:120],
                "passed": False, "checks": {}, "errors": [f"planner_error: {type(exc).__name__}"],
                "step_count": 0,
            })
    passed = sum(1 for item in results if item["passed"])
    run = {
        "run_id": uuid.uuid4().hex,
        "created_at": time.time(),
        "passed": passed,
        "total": len(results),
        "score": round(passed / len(results), 4) if results else 0.0,
        "results": results,
        "mode": "offline_deterministic_regression",
        "execution_performed": False,
        "model_training_performed": False,
    }
    with _connect() as db:
        db.execute(
            "INSERT INTO evaluation_runs VALUES(?,?,?,?,?,?)",
            (run["run_id"], run["created_at"], run["passed"], run["total"],
             run["score"], json.dumps(run["results"], ensure_ascii=False)),
        )
    return run


@post("/api/evaluation/run", sync_to_thread=True)
def evaluation_run(request: Request) -> dict[str, Any]:
    _require_admin(request)
    return run_evaluation()


@get("/api/evaluation/runs", sync_to_thread=True)
def evaluation_runs(request: Request, limit: int = 10) -> dict[str, Any]:
    _require_admin(request)
    limit = max(1, min(int(limit), 50))
    with _connect() as db:
        rows = db.execute(
            "SELECT run_id,created_at,passed,total,score,results_json "
            "FROM evaluation_runs ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    items = []
    for row in rows:
        item = dict(row)
        item["results"] = json.loads(item.pop("results_json"))
        items.append(item)
    return {"items": items, "execution_performed": False}

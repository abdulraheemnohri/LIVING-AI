"""Regression promotion gate based on persisted offline evaluation runs.

This gate records decisions only. It never deploys code, changes model weights,
approves goals, or enables worker execution.
"""
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

DEFAULT_WINDOW = 3
MAX_WINDOW = 10
DEFAULT_MIN_SCORE = 1.0


@contextmanager
def _connect():
    db = sqlite3.connect(data_dir() / "evaluation_runs.sqlite3", timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("""CREATE TABLE IF NOT EXISTS gate_decisions (
        decision_id TEXT PRIMARY KEY, created_at REAL NOT NULL,
        eligible INTEGER NOT NULL, window_size INTEGER NOT NULL,
        min_score REAL NOT NULL, run_ids_json TEXT NOT NULL,
        reasons_json TEXT NOT NULL, recommendations_json TEXT NOT NULL
    )""")
    try:
        yield db
        db.commit()
    finally:
        db.close()


def _require_admin(request: Request) -> None:
    token = os.getenv("LIVING_AI_ADMIN_TOKEN", "").strip()
    if not token:
        raise HTTPException(status_code=503, detail="Promotion gate is locked: configure LIVING_AI_ADMIN_TOKEN and restart")
    if request.headers.get("authorization", "") != f"Bearer {token}":
        raise HTTPException(status_code=401, detail="Valid admin bearer token required")


def assess_gate(*, window: int = DEFAULT_WINDOW, min_score: float = DEFAULT_MIN_SCORE) -> dict[str, Any]:
    """Assess recent saved evaluations; missing history and regressions fail closed."""
    window = max(1, min(int(window), MAX_WINDOW))
    min_score = max(0.0, min(1.0, float(min_score)))
    with _connect() as db:
        rows = db.execute(
            "SELECT run_id,created_at,passed,total,score,results_json "
            "FROM evaluation_runs ORDER BY created_at DESC LIMIT ?",
            (window + 1,),
        ).fetchall()

    recent = [dict(row) for row in rows[:window]]
    baseline = dict(rows[window]) if len(rows) > window else None
    reasons: list[str] = []
    recommendations: list[str] = []
    if len(recent) < window:
        reasons.append(f"Need {window} recent evaluation runs; found {len(recent)}.")
        recommendations.append("Run the offline regression suite until the required history window is available.")
    for run in recent:
        if int(run["total"]) <= 0:
            reasons.append(f"Run {run['run_id']} has no test cases.")
        if float(run["score"]) < min_score:
            reasons.append(f"Run {run['run_id']} scored {float(run['score']):.0%}, below the {min_score:.0%} threshold.")
        try:
            results = json.loads(run["results_json"])
        except (TypeError, json.JSONDecodeError):
            results = []
            reasons.append(f"Run {run['run_id']} has invalid result data.")
        failures = [item for item in results if not item.get("passed")]
        for failed in failures:
            case_id = str(failed.get("case_id", "unknown"))
            checks = ", ".join(str(c) for c in failed.get("errors", [])) or "inspect case details"
            recommendation = f"Fix regression case '{case_id}': {checks}."
            if recommendation not in recommendations:
                recommendations.append(recommendation)

    if baseline is not None and recent:
        latest_score = float(recent[0]["score"])
        baseline_score = float(baseline["score"])
        if latest_score < baseline_score:
            reasons.append(
                f"Latest score regressed from baseline {baseline_score:.0%} to {latest_score:.0%}."
            )
            recommendations.append("Investigate the latest score drop and rerun the suite before reconsidering promotion.")

    if not recommendations and not reasons:
        recommendations.append("Regression window is clean. A human may review promotion; this endpoint does not promote anything.")
    eligible = not reasons
    decision = {
        "decision_id": uuid.uuid4().hex,
        "created_at": time.time(),
        "eligible": eligible,
        "status": "eligible_for_human_review" if eligible else "blocked",
        "window_size": window,
        "min_score": min_score,
        "runs_checked": len(recent),
        "run_ids": [str(run["run_id"]) for run in recent],
        "scores": [float(run["score"]) for run in recent],
        "reasons": reasons,
        "recommendations": recommendations,
        "promotion_performed": False,
        "deployment_performed": False,
        "model_training_performed": False,
    }
    with _connect() as db:
        db.execute(
            "INSERT INTO gate_decisions VALUES(?,?,?,?,?,?,?,?)",
            (decision["decision_id"], decision["created_at"], int(eligible), window, min_score,
             json.dumps(decision["run_ids"]), json.dumps(reasons), json.dumps(recommendations)),
        )
    return decision


@post("/api/evaluation/gate/check", sync_to_thread=True)
def evaluation_gate_check(request: Request, window: int = DEFAULT_WINDOW,
                          min_score: float = DEFAULT_MIN_SCORE) -> dict[str, Any]:
    _require_admin(request)
    if not 1 <= int(window) <= MAX_WINDOW:
        raise HTTPException(status_code=400, detail=f"window must be between 1 and {MAX_WINDOW}")
    if not 0.0 <= float(min_score) <= 1.0:
        raise HTTPException(status_code=400, detail="min_score must be between 0 and 1")
    return assess_gate(window=window, min_score=min_score)


@get("/api/evaluation/gate/history", sync_to_thread=True)
def evaluation_gate_history(request: Request, limit: int = 10) -> dict[str, Any]:
    _require_admin(request)
    limit = max(1, min(int(limit), 50))
    with _connect() as db:
        rows = db.execute(
            "SELECT decision_id,created_at,eligible,window_size,min_score,run_ids_json,reasons_json,recommendations_json "
            "FROM gate_decisions ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    items = []
    for row in rows:
        item = dict(row)
        item["eligible"] = bool(item["eligible"])
        item["run_ids"] = json.loads(item.pop("run_ids_json"))
        item["reasons"] = json.loads(item.pop("reasons_json"))
        item["recommendations"] = json.loads(item.pop("recommendations_json"))
        item["promotion_performed"] = False
        items.append(item)
    return {"items": items, "promotion_performed": False}

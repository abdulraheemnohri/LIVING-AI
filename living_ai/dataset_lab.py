"""Human-reviewed training-example curation for the local learning pipeline.

Only explicitly approved examples are exported. This module does not train models.
"""
from __future__ import annotations
import hmac

import hashlib
import json
import os
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from litestar import Request, get, post
from litestar.exceptions import HTTPException

from .db import data_dir

MAX_INPUT_CHARS = 8000
MAX_OUTPUT_CHARS = 12000
MAX_EXPORT_ROWS = 5000


@contextmanager
def _connect():
    root = data_dir()
    root.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(root / "curated_dataset.sqlite3", timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("""CREATE TABLE IF NOT EXISTS curated_examples (
        example_id TEXT PRIMARY KEY,
        fingerprint TEXT NOT NULL UNIQUE,
        user_input TEXT NOT NULL,
        expected_output TEXT NOT NULL,
        source TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('pending','approved','rejected')),
        created_at REAL NOT NULL,
        reviewed_at REAL
    )""")
    try:
        yield db
        db.commit()
    finally:
        db.close()


def _require_admin(request: Request) -> None:
    password = os.getenv("LIVING_AI_ADMIN_PASSWORD", "").strip()
    if not password:
        raise HTTPException(status_code=503, detail="Dataset Lab is locked: configure LIVING_AI_ADMIN_PASSWORD and restart")
    if not hmac.compare_digest(request.headers.get("x-admin-password", ""), password):
        raise HTTPException(status_code=401, detail="Valid admin password required")


def _clean_text(value: Any, field: str, limit: int) -> str:
    if not isinstance(value, str):
        raise HTTPException(status_code=400, detail=f"{field} must be text")
    value = value.strip()
    if not value:
        raise HTTPException(status_code=400, detail=f"{field} cannot be empty")
    if len(value) > limit:
        raise HTTPException(status_code=400, detail=f"{field} exceeds {limit} characters")
    return value


@post("/api/dataset/examples", sync_to_thread=True)
def dataset_add_example(data: dict[str, Any], request: Request) -> dict[str, Any]:
    _require_admin(request)
    user_input = _clean_text(data.get("input"), "input", MAX_INPUT_CHARS)
    expected_output = _clean_text(data.get("expected_output"), "expected_output", MAX_OUTPUT_CHARS)
    source = _clean_text(data.get("source", "manual"), "source", 200)
    fingerprint = hashlib.sha256(
        (user_input + "\0" + expected_output).encode("utf-8")
    ).hexdigest()
    example_id = uuid.uuid4().hex
    created_at = time.time()
    with _connect() as db:
        existing = db.execute(
            "SELECT example_id,status FROM curated_examples WHERE fingerprint=?", (fingerprint,)
        ).fetchone()
        if existing:
            return {"created": False, "duplicate": True, "example_id": existing["example_id"],
                    "status": existing["status"], "exported": False}
        db.execute(
            "INSERT INTO curated_examples VALUES(?,?,?,?,?,?,?,NULL)",
            (example_id, fingerprint, user_input, expected_output, source, "pending", created_at),
        )
    return {"created": True, "duplicate": False, "example_id": example_id,
            "status": "pending", "exported": False}


@get("/api/dataset/examples", sync_to_thread=True)
def dataset_list_examples(request: Request, status: str = "all", limit: int = 100) -> dict[str, Any]:
    _require_admin(request)
    if status not in {"all", "pending", "approved", "rejected"}:
        raise HTTPException(status_code=400, detail="status must be all, pending, approved, or rejected")
    limit = max(1, min(int(limit), 500))
    with _connect() as db:
        if status == "all":
            rows = db.execute(
                "SELECT example_id,user_input,expected_output,source,status,created_at,reviewed_at "
                "FROM curated_examples ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        else:
            rows = db.execute(
                "SELECT example_id,user_input,expected_output,source,status,created_at,reviewed_at "
                "FROM curated_examples WHERE status=? ORDER BY created_at DESC LIMIT ?", (status, limit)
            ).fetchall()
    return {"items": [dict(row) for row in rows], "count": len(rows)}


@post("/api/dataset/examples/{example_id:str}/review", sync_to_thread=True)
def dataset_review_example(example_id: str, data: dict[str, Any], request: Request) -> dict[str, Any]:
    _require_admin(request)
    decision = data.get("decision")
    if decision not in {"approved", "rejected", "pending"}:
        raise HTTPException(status_code=400, detail="decision must be approved, rejected, or pending")
    with _connect() as db:
        cursor = db.execute(
            "UPDATE curated_examples SET status=?,reviewed_at=? WHERE example_id=?",
            (decision, time.time(), example_id),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Dataset example not found")
    return {"example_id": example_id, "status": decision, "exported": False}


@post("/api/dataset/export", sync_to_thread=True)
def dataset_export(request: Request) -> dict[str, Any]:
    _require_admin(request)
    root = data_dir()
    target_dir = root / "corpus"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / "curated_training.jsonl"
    with _connect() as db:
        rows = db.execute(
            "SELECT example_id,user_input,expected_output,source,created_at "
            "FROM curated_examples WHERE status='approved' ORDER BY created_at ASC LIMIT ?",
            (MAX_EXPORT_ROWS,),
        ).fetchall()
    lines = [
        json.dumps({"id": row["example_id"], "input": row["user_input"],
                    "output": row["expected_output"], "source": row["source"],
                    "created_at": row["created_at"]}, ensure_ascii=False)
        for row in rows
    ]
    temporary = target.with_suffix(".jsonl.tmp")
    temporary.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    temporary.replace(target)
    return {"exported": len(lines), "path": str(target), "format": "jsonl",
            "approved_only": True, "model_training_performed": False}

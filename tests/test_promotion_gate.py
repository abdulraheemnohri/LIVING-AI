import json
import os
import sqlite3
import time

import pytest
from litestar.testing import TestClient

from living_ai.app import app
import living_ai.planner_api as planner_api
import living_ai.worker_api as worker_api


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("LIVING_AI_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("LIVING_AI_ADMIN_PASSWORD", "test-admin-password")
    planner_api._engine = None
    planner_api._coordinator_instance = None
    worker_api._worker = None
    with TestClient(app) as test_client:
        yield test_client
    planner_api._engine = None
    planner_api._coordinator_instance = None
    worker_api._worker = None


def _seed_runs(tmp_path, scores):
    db = sqlite3.connect(tmp_path / "evaluation_runs.sqlite3")
    db.execute("""CREATE TABLE IF NOT EXISTS evaluation_runs (
        run_id TEXT PRIMARY KEY, created_at REAL NOT NULL, passed INTEGER NOT NULL,
        total INTEGER NOT NULL, score REAL NOT NULL, results_json TEXT NOT NULL
    )""")
    now = time.time()
    for index, score in enumerate(scores):
        passed_count = round(score * 8)
        results = [
            {"case_id": f"case-{case_index}", "passed": case_index < passed_count,
             "errors": [] if case_index < passed_count else ["actions_allowlisted"]}
            for case_index in range(8)
        ]
        db.execute("INSERT INTO evaluation_runs VALUES(?,?,?,?,?,?)",
                   (f"run-{index}", now + index, passed_count, 8, round(passed_count / 8, 4), json.dumps(results)))
    db.commit()
    db.close()


def test_gate_fails_closed_when_no_evaluation_history_exists(client):
    response = client.post("/api/evaluation/gate/check?window=3&min_score=1.0",
                           headers={"X-Admin-Password": "test-admin-password"}, json={})
    assert response.status_code == 201
    result = response.json()
    assert result["eligible"] is False
    assert result["runs_checked"] == 0
    assert any("Need 3 recent" in reason for reason in result["reasons"])


def test_gate_fails_closed_when_history_is_too_short(client, tmp_path):
    _seed_runs(tmp_path, [1.0, 1.0])
    response = client.post("/api/evaluation/gate/check?window=3&min_score=1.0",
                           headers={"X-Admin-Password": "test-admin-password"}, json={})
    assert response.status_code == 201
    result = response.json()
    assert result["eligible"] is False
    assert result["promotion_performed"] is False
    assert any("Need 3 recent" in reason for reason in result["reasons"])


def test_gate_blocks_a_regression_and_persists_decision(client, tmp_path):
    _seed_runs(tmp_path, [1.0, 1.0, 0.75, 0.5])
    headers = {"X-Admin-Password": "test-admin-password"}
    response = client.post("/api/evaluation/gate/check?window=3&min_score=0.7", headers=headers, json={})
    assert response.status_code == 201
    result = response.json()
    assert result["eligible"] is False
    assert result["promotion_performed"] is False
    history = client.get("/api/evaluation/gate/history", headers=headers)
    assert history.status_code == 200
    assert history.json()["items"][0]["decision_id"] == result["decision_id"]


def test_gate_allows_clean_window_only_for_human_review(client, tmp_path):
    _seed_runs(tmp_path, [0.875, 1.0, 1.0, 1.0])
    response = client.post("/api/evaluation/gate/check?window=3&min_score=1.0",
                           headers={"X-Admin-Password": "test-admin-password"}, json={})
    assert response.status_code == 201
    result = response.json()
    assert result["eligible"] is True
    assert result["status"] == "eligible_for_human_review"
    assert result["promotion_performed"] is False


def test_gate_endpoints_fail_closed_without_admin_token(client, monkeypatch):
    monkeypatch.delenv("LIVING_AI_ADMIN_PASSWORD")
    response = client.post("/api/evaluation/gate/check", json={})
    assert response.status_code == 503

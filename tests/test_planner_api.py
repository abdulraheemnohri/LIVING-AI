import pytest
from litestar.testing import TestClient

from living_ai.app import app
import living_ai.planner_api as planner_api


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("LIVING_AI_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("LIVING_AI_ADMIN_TOKEN", "test-admin-token")
    monkeypatch.setenv("LIVING_AI_ALLOW_REMOTE_PROVIDER", "false")
    planner_api._engine = None
    planner_api._coordinator_instance = None
    with TestClient(app) as test_client:
        yield test_client
    planner_api._engine = None
    planner_api._coordinator_instance = None


def test_prepare_is_persistent_and_does_not_submit(client):
    headers = {"Authorization": "Bearer test-admin-token"}
    response = client.post(
        "/api/planner/prepare",
        headers=headers,
        json={"goal": "Improve offline search. Add regression tests."},
    )
    assert response.status_code == 201
    prepared = response.json()
    assert prepared["submitted"] is False
    assert prepared["execution_performed"] is False
    assert prepared["plan"]["steps"]
    plans = client.get("/api/planner/proposals", headers=headers)
    assert plans.status_code == 200
    assert plans.json()["items"][0]["plan_id"] == prepared["plan"]["plan_id"]


def test_submit_queues_plan_without_executing_and_rejects_duplicate(client):
    headers = {"Authorization": "Bearer test-admin-token"}
    prepared = client.post(
        "/api/planner/prepare", headers=headers, json={"goal": "Write a small note."}
    ).json()
    plan_id = prepared["plan"]["plan_id"]
    submitted = client.post(
        "/api/planner/submit", headers=headers, json={"plan_id": plan_id}
    )
    assert submitted.status_code == 201
    result = submitted.json()
    assert result["submitted"] is True
    assert result["execution_performed"] is False
    assert result["queued_count"] >= 1
    duplicate = client.post(
        "/api/planner/submit", headers=headers, json={"plan_id": plan_id}
    )
    assert duplicate.status_code == 409


def test_evaluation_is_saved_to_local_learning_memory(client):
    headers = {"Authorization": "Bearer test-admin-token"}
    response = client.post(
        "/api/planner/evaluations",
        headers=headers,
        json={
            "goal": "Improve offline search",
            "score": 0.85,
            "outcome": "Manual review successful",
            "feedback": "Keep it local",
            "tags": ["search"],
        },
    )
    assert response.status_code == 201
    summary = client.get("/api/planner/learning-summary", headers=headers)
    assert summary.status_code == 200
    assert summary.json()["evaluations"] == 1


def test_planner_routes_fail_closed_without_admin_token(client, monkeypatch):
    monkeypatch.delenv("LIVING_AI_ADMIN_TOKEN")
    response = client.get("/api/planner/proposals")
    assert response.status_code == 503

import pytest
from litestar.testing import TestClient

from living_ai.app import app
import living_ai.planner_api as planner_api
import living_ai.worker_api as worker_api


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("LIVING_AI_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("LIVING_AI_ADMIN_PASSWORD", "test-admin-password")
    monkeypatch.setenv("LIVING_AI_ALLOW_REMOTE_PROVIDER", "false")
    planner_api._engine = None
    planner_api._coordinator_instance = None
    worker_api._worker = None
    with TestClient(app) as test_client:
        yield test_client
    planner_api._engine = None
    planner_api._coordinator_instance = None
    worker_api._worker = None


def test_worker_starts_paused_and_does_not_tick_while_paused(client):
    headers = {"X-Admin-Password": "test-admin-password"}
    status = client.get("/api/worker/status", headers=headers)
    assert status.status_code == 200
    assert status.json()["worker"]["paused"] is True
    tick = client.post("/api/worker/tick", headers=headers, json={})
    assert tick.status_code == 201
    assert tick.json()["status"] == "paused"
    assert tick.json()["execution_performed"] is False


def test_planner_goals_require_approval_before_worker_can_execute(client):
    headers = {"X-Admin-Password": "test-admin-password"}
    prepared = client.post(
        "/api/planner/prepare", headers=headers, json={"goal": "Record a reviewable note."}
    ).json()
    submitted = client.post(
        "/api/planner/submit", headers=headers, json={"plan_id": prepared["plan"]["plan_id"]}
    )
    assert submitted.status_code == 201
    goal_id = submitted.json()["goal_ids"][0]

    before = client.get("/api/worker/status", headers=headers).json()
    goal = next(g for g in before["goals"] if g["id"] == goal_id)
    assert goal["status"] == "needs_approval"

    resumed = client.post("/api/worker/resume", headers=headers, json={})
    assert resumed.status_code == 201
    tick = client.post("/api/worker/tick", headers=headers, json={})
    assert tick.status_code == 201
    assert tick.json()["results"] == []
    held = next(g for g in client.get("/api/worker/status", headers=headers).json()["goals"] if g["id"] == goal_id)
    assert held["status"] == "needs_approval"

    approval = client.post(f"/api/worker/goals/{goal_id}/approve", headers=headers, json={})
    assert approval.status_code == 201
    assert approval.json()["execution_performed"] is False
    tick = client.post("/api/worker/tick", headers=headers, json={})
    assert tick.status_code == 201
    assert any(result["goal_id"] == goal_id and result["status"] == "completed" for result in tick.json()["results"])


def test_worker_controls_require_admin_password(client, monkeypatch):
    monkeypatch.delenv("LIVING_AI_ADMIN_PASSWORD")
    response = client.post("/api/worker/resume", json={})
    assert response.status_code == 503

def test_private_read_endpoints_fail_closed_without_admin_password(client, monkeypatch):
    monkeypatch.delenv("LIVING_AI_ADMIN_PASSWORD")
    paths = [
        "/api/status",
        "/api/model/status",
        "/api/memories",
        "/api/training/datasets",
        "/api/training/history",
        "/api/evolution/proposals",
        "/api/audit",
        "/api/settings",
        "/api/worker/status",
        "/api/evaluation/runs",
        "/api/evaluation/gate/history",
        "/api/dataset/examples",
    ]
    for path in paths:
        response = client.get(path)
        assert response.status_code == 503, f"{path} returned {response.status_code}"


def test_private_read_endpoints_reject_incorrect_admin_password(client):
    paths = [
        "/api/status",
        "/api/model/status",
        "/api/memories",
        "/api/training/datasets",
        "/api/training/history",
        "/api/evolution/proposals",
        "/api/audit",
        "/api/settings",
        "/api/worker/status",
        "/api/evaluation/runs",
        "/api/evaluation/gate/history",
        "/api/dataset/examples",
    ]
    headers = {"X-Admin-Password": "definitely-wrong-password"}
    for path in paths:
        response = client.get(path, headers=headers)
        assert response.status_code == 401, f"{path} returned {response.status_code}"



def test_sensitive_mutations_reject_missing_admin_password(client, monkeypatch):
    monkeypatch.delenv("LIVING_AI_ADMIN_PASSWORD")
    cases = [
        ("/api/knowledge/ingest", {"content": "private data", "source": "test"}),
        ("/api/training/train", {"input_dir": "data/corpus"}),
        ("/api/evaluation/run", {}),
        ("/api/dataset/examples", {"input": "test input", "expected_output": "test output"}),
        ("/api/tasks", {"title": "test", "action": "save_note", "payload": {"text": "hello"}}),
    ]
    for path, payload in cases:
        response = client.post(path, json=payload)
        assert response.status_code == 503, f"{path} returned {response.status_code}"


def test_sensitive_mutations_reject_wrong_admin_password(client):
    headers = {"X-Admin-Password": "definitely-wrong-password"}
    cases = [
        ("/api/knowledge/ingest", {"content": "private data", "source": "test"}),
        ("/api/training/train", {"input_dir": "data/corpus"}),
        ("/api/evaluation/run", {}),
        ("/api/dataset/examples", {"input": "test input", "expected_output": "test output"}),
        ("/api/tasks", {"title": "test", "action": "save_note", "payload": {"text": "hello"}}),
    ]
    for path, payload in cases:
        response = client.post(path, headers=headers, json=payload)
        assert response.status_code == 401, f"{path} returned {response.status_code}"

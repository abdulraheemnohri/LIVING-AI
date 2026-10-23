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


def test_evaluation_run_is_offline_bounded_and_persistent(client):
    headers = {"X-Admin-Password": "test-admin-password"}
    response = client.post("/api/evaluation/run", headers=headers, json={})
    assert response.status_code == 201
    run = response.json()
    assert run["execution_performed"] is False
    assert run["model_training_performed"] is False
    assert run["mode"] == "offline_deterministic_regression"
    assert run["total"] == 8
    assert run["passed"] == 8
    assert all(item["passed"] for item in run["results"])
    history = client.get("/api/evaluation/runs", headers=headers)
    assert history.status_code == 200
    assert history.json()["items"][0]["run_id"] == run["run_id"]


def test_evaluation_endpoints_fail_closed_without_admin_token(client, monkeypatch):
    monkeypatch.delenv("LIVING_AI_ADMIN_PASSWORD")
    response = client.post("/api/evaluation/run", json={})
    assert response.status_code == 503

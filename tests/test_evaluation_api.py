import pytest
from litestar.testing import TestClient

from living_ai.app import app


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("LIVING_AI_ADMIN_TOKEN", "test-token")
    monkeypatch.setenv("LIVING_AI_DATA_DIR", str(tmp_path))
    with TestClient(app=app) as c:
        yield c


def headers():
    return {"Authorization": "Bearer test-token"}


def test_evaluation_lab_fails_closed_without_token(monkeypatch, tmp_path):
    monkeypatch.delenv("LIVING_AI_ADMIN_TOKEN", raising=False)
    monkeypatch.setenv("LIVING_AI_DATA_DIR", str(tmp_path))
    with TestClient(app=app) as c:
        response = c.get("/api/evaluations/summary")
    assert response.status_code == 503


def test_record_search_and_summary_are_persistent(client):
    payload = {
        "goal": "Improve Urdu document retrieval",
        "score": 0.9,
        "outcome": "Relevant Urdu notes were found",
        "feedback": "Good lexical overlap; test spelling variants",
        "plan_summary": "Index local Urdu Markdown notes",
        "tags": ["urdu", "retrieval"],
    }
    response = client.post("/api/evaluations", json=payload, headers=headers())
    assert response.status_code in (200, 201)
    assert response.json()["training_performed"] is False
    found = client.get("/api/evaluations?q=Urdu", headers=headers())
    assert found.status_code == 200
    assert found.json()["items"][0]["goal"] == payload["goal"]
    summary = client.get("/api/evaluations/summary", headers=headers())
    assert summary.json()["evaluations"] == 1
    assert summary.json()["average_score"] == 0.9


def test_invalid_score_is_rejected(client):
    response = client.post("/api/evaluations", json={
        "goal": "Test", "score": 2, "outcome": "bad score"
    }, headers=headers())
    assert response.status_code == 400

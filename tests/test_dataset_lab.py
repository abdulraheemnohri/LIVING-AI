import json
import os

import pytest
from litestar.testing import TestClient

from living_ai.app import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("LIVING_AI_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("LIVING_AI_ADMIN_TOKEN", "dataset-test-token")
    with TestClient(app) as test_client:
        yield test_client


def headers():
    return {"Authorization": "Bearer dataset-test-token"}


def add_example(client, text="Explain safe maintenance.", output="Inspect the circuit with isolation."):
    return client.post("/api/dataset/examples", headers=headers(),
                       json={"input": text, "expected_output": output, "source": "test"})


def test_examples_are_pending_until_explicit_review(client):
    created = add_example(client)
    assert created.status_code == 201
    item = created.json()
    assert item["status"] == "pending"
    listed = client.get("/api/dataset/examples?status=pending", headers=headers()).json()
    assert listed["count"] == 1
    assert listed["items"][0]["status"] == "pending"


def test_duplicate_examples_are_deduplicated(client):
    first = add_example(client)
    second = add_example(client)
    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json()["duplicate"] is True
    assert first.json()["example_id"] == second.json()["example_id"]


def test_only_approved_examples_are_exported_as_unicode_jsonl(client, tmp_path):
    first = add_example(client, "بجلی کی حفاظت", "پہلے بجلی بند کریں۔")
    second = add_example(client, "Rejected input", "Do not use.")
    assert first.status_code == 201 and second.status_code == 201
    review = client.post(f"/api/dataset/examples/{first.json()['example_id']}/review",
                         headers=headers(), json={"decision": "approved"})
    assert review.status_code == 201
    exported = client.post("/api/dataset/export", headers=headers(), json={})
    assert exported.status_code == 201
    payload = exported.json()
    assert payload["exported"] == 1
    assert payload["model_training_performed"] is False
    rows = (tmp_path / "corpus" / "curated_training.jsonl").read_text(encoding="utf-8").splitlines()
    record = json.loads(rows[0])
    assert record["input"] == "بجلی کی حفاظت"
    assert record["output"] == "پہلے بجلی بند کریں۔"
    assert len(rows) == 1


def test_dataset_api_fails_closed_without_admin_token(client, monkeypatch):
    monkeypatch.delenv("LIVING_AI_ADMIN_TOKEN")
    response = client.get("/api/dataset/examples")
    assert response.status_code == 503


def test_invalid_review_decision_is_rejected(client):
    created = add_example(client)
    response = client.post(f"/api/dataset/examples/{created.json()['example_id']}/review",
                           headers=headers(), json={"decision": "ship"})
    assert response.status_code == 400

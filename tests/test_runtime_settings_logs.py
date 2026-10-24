import pytest
from litestar.testing import TestClient
from living_ai.app import app
from living_ai.db import init_db

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("LIVING_AI_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("LIVING_AI_ADMIN_PASSWORD", "runtime-test-password")
    monkeypatch.setenv("LIVING_AI_LOG_LEVEL", "INFO")
    with TestClient(app) as c:
        yield c

def test_runtime_settings_update_and_validation(client):
    h={"X-Admin-Password":"runtime-test-password"}
    response=client.post("/api/settings",headers=h,json={"temperature":0.4,"max_reply_chars":2200,"retrieval_limit":7,"log_level":"DEBUG"})
    assert response.status_code==200, response.text
    assert response.json()["settings"]["temperature"]==0.4
    assert response.json()["settings"]["max_reply_chars"]==2200
    assert response.json()["logging"]["level"]=="DEBUG"
    invalid=client.post("/api/settings",headers=h,json={"temperature":0.9,"log_level":"LOUD"})
    assert invalid.status_code==400
    current=client.get("/api/settings",headers=h).json()["settings"]
    assert current["temperature"]==0.4

def test_logs_are_persistent_exportable_and_protected(client):
    h={"X-Admin-Password":"runtime-test-password"}
    assert client.get("/api/logs").status_code==401
    response=client.post("/api/settings",headers=h,json={"log_level":"INFO"})
    assert response.status_code==200
    from living_ai.logging_store import get_logger
    get_logger("tests").warning("test persistent log marker")
    listing=client.get("/api/logs?limit=100",headers=h)
    assert listing.status_code==200
    assert any("test persistent log marker" in line for line in listing.json()["items"])
    exported=client.get("/api/logs/export",headers=h)
    assert exported.status_code==200
    assert "test persistent log marker" in exported.text
    cleared=client.post("/api/logs/clear",headers=h,json={})
    assert cleared.status_code==200
    after=client.get("/api/logs",headers=h).json()["items"]
    assert any("cleared by administrator" in line for line in after)

def test_runtime_settings_and_log_routes_fail_closed(client,monkeypatch):
    monkeypatch.delenv("LIVING_AI_ADMIN_PASSWORD")
    assert client.get("/api/settings").status_code==503
    assert client.post("/api/settings",json={"temperature":0.5}).status_code==503
    assert client.get("/api/logs").status_code==503

def test_rotated_logs_are_included_in_export(client, monkeypatch):
    from living_ai.logging_store import log_path, configure_logging
    configure_logging("INFO")
    path=log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.with_name(path.name + ".1").write_text("2026-01-01 00:00:00,000 WARNING living_ai.tests rotated-history-marker\\n", encoding="utf-8")
    h={"X-Admin-Password":"runtime-test-password"}
    listing=client.get("/api/logs?limit=200",headers=h)
    assert listing.status_code==200, listing.text
    assert any("rotated-history-marker" in line for line in listing.json()["items"])
    exported=client.get("/api/logs/export",headers=h)
    assert exported.status_code==200
    assert "rotated-history-marker" in exported.text

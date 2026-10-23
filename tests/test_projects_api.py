import pytest
from litestar.testing import TestClient
from living_ai.app import app

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("LIVING_AI_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("LIVING_AI_ADMIN_PASSWORD", "project-test-password")
    with TestClient(app) as c:
        yield c

def test_project_management_create_update_and_delete_work_items(client):
    h={"X-Admin-Password":"project-test-password"}
    p=client.post("/api/projects",headers=h,json={"name":"LIVING-AI release","description":"Ship a reviewed release","priority":"high","due_date":""})
    assert p.status_code in (200,201), p.text
    project=p.json(); pid=project["id"]
    item=client.post(f"/api/projects/{pid}/items",headers=h,json={"title":"Build dashboard","status":"todo","priority":"critical"})
    assert item.status_code in (200,201), item.text
    wid=item.json()["id"]
    changed=client.patch(f"/api/projects/{pid}/items/{wid}",headers=h,json={"title":"Build dashboard","description":"Responsive project UI","status":"done","priority":"high","due_date":""})
    assert changed.status_code==200, changed.text
    assert changed.json()["status"]=="done"
    listing=client.get("/api/projects",headers=h)
    assert listing.status_code==200
    found=next(x for x in listing.json()["items"] if x["id"]==pid)
    assert found["progress"]==100
    assert found["completed_count"]==1
    deleted=client.delete(f"/api/projects/{pid}",headers=h)
    assert deleted.status_code==200
    assert client.get(f"/api/projects/{pid}/items",headers=h).status_code==404

def test_project_management_fails_closed_without_password(client,monkeypatch):
    monkeypatch.delenv("LIVING_AI_ADMIN_PASSWORD")
    assert client.get("/api/projects").status_code==503
    assert client.post("/api/projects",json={"name":"Should not save"}).status_code==503

def test_project_management_rejects_invalid_status(client):
    response=client.post("/api/projects",headers={"X-Admin-Password":"project-test-password"},json={"name":"Bad status","status":"executed"})
    assert response.status_code==400

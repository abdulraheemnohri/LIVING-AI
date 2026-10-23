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

def test_project_backup_export_and_import(client):
    h={"X-Admin-Password":"project-test-password"}
    p=client.post("/api/projects",headers=h,json={"name":"Backup sample","description":"portable backup"})
    assert p.status_code in (200,201), p.text
    pid=p.json()["id"]
    m=client.post(f"/api/projects/{pid}/milestones",headers=h,json={"title":"Beta","status":"planned"})
    assert m.status_code in (200,201), m.text
    w=client.post(f"/api/projects/{pid}/items",headers=h,json={"title":"First task","status":"todo","milestone_id":m.json()["id"]})
    assert w.status_code in (200,201), w.text
    backup=client.get("/api/projects/export",headers=h)
    assert backup.status_code==200, backup.text
    payload=backup.json()
    assert payload["format"]=="living-ai-projects"
    assert len(payload["projects"])==1 and len(payload["milestones"])==1 and len(payload["work_items"])==1
    restored=client.post("/api/projects/import",headers=h,json=payload)
    assert restored.status_code in (200,201), restored.text
    assert restored.json()["projects"]==1
    assert restored.json()["milestones"]==1
    assert restored.json()["work_items"]==1
    listing=client.get("/api/projects",headers=h)
    assert listing.status_code==200
    assert listing.json()["summary"]["projects"]==2

def test_project_import_rejects_wrong_format(client):
    h={"X-Admin-Password":"project-test-password"}
    response=client.post("/api/projects/import",headers=h,json={"format":"wrong","version":1,"projects":[]})
    assert response.status_code==400

def test_deleting_prerequisite_clears_dependent_task_link(client):
    h={"X-Admin-Password":"project-test-password"}
    p=client.post("/api/projects",headers=h,json={"name":"Dependency cleanup"})
    assert p.status_code in (200,201), p.text
    pid=p.json()["id"]
    first=client.post(f"/api/projects/{pid}/items",headers=h,json={"title":"Prerequisite","status":"todo"})
    assert first.status_code in (200,201), first.text
    first_id=first.json()["id"]
    second=client.post(f"/api/projects/{pid}/items",headers=h,json={"title":"Dependent","status":"todo","dependency_id":first_id})
    assert second.status_code in (200,201), second.text
    second_id=second.json()["id"]
    deleted=client.delete(f"/api/projects/{pid}/items/{first_id}",headers=h)
    assert deleted.status_code==200, deleted.text
    items=client.get(f"/api/projects/{pid}/items",headers=h)
    assert items.status_code==200, items.text
    remaining=next(x for x in items.json()["items"] if x["id"]==second_id)
    assert remaining["dependency_id"] is None
    activity=client.get(f"/api/projects/{pid}/activity",headers=h)
    assert activity.status_code==200, activity.text
    assert any(x["action"]=="dependencies_cleared" for x in activity.json()["items"])

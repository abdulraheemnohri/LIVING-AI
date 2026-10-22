import pytest

from living_ai.autonomous import Action, AutonomyEngine
from living_ai.lifecycle import TaskLifecycle


def test_submit_and_run_tracks_completed_task(tmp_path):
    engine = AutonomyEngine(tmp_path / "engine.sqlite3")
    tasks = TaskLifecycle(engine, tmp_path / "lifecycle.sqlite3")
    task = tasks.submit("save a note", "save_note", {"text": "hello"})
    assert task["status"] == "queued"
    result = tasks.run_once()
    assert result[0]["task_id"] == task["task_id"]
    assert result[0]["status"] == "completed"
    assert len(engine.list_notes()) == 1
    assert [e["event"] for e in tasks.events(task["task_id"])]


def test_failed_task_has_bounded_explicit_retries(tmp_path):
    engine = AutonomyEngine(tmp_path / "engine.sqlite3")
    engine.register_action(Action("fail_action", lambda payload: (_ for _ in ()).throw(RuntimeError("expected")), True))
    tasks = TaskLifecycle(engine, tmp_path / "lifecycle.sqlite3", max_retries=1)
    task = tasks.submit("expected failure", "fail_action", {})
    task = tasks.run_once()[0]
    assert task["status"] == "failed"
    retried = tasks.retry_failed(task["task_id"])
    assert retried["status"] == "queued"
    assert retried["attempts"] == 2
    failed_again = tasks.run_once()[0]
    assert failed_again["status"] == "failed"
    with pytest.raises(ValueError, match="retry budget"):
        tasks.retry_failed(task["task_id"])


def test_unknown_action_rejected_at_submission(tmp_path):
    engine = AutonomyEngine(tmp_path / "engine.sqlite3")
    tasks = TaskLifecycle(engine, tmp_path / "lifecycle.sqlite3")
    with pytest.raises(ValueError, match="registered"):
        tasks.submit("not allowed", "shell_command", {})


def test_retry_only_failed_tasks(tmp_path):
    engine = AutonomyEngine(tmp_path / "engine.sqlite3")
    tasks = TaskLifecycle(engine, tmp_path / "lifecycle.sqlite3")
    task = tasks.submit("save", "save_note", {"text": "safe"})
    with pytest.raises(ValueError, match="only failed"):
        tasks.retry_failed(task["task_id"])


def test_payload_size_is_bounded(tmp_path):
    engine = AutonomyEngine(tmp_path / "engine.sqlite3")
    tasks = TaskLifecycle(engine, tmp_path / "lifecycle.sqlite3")
    with pytest.raises(ValueError, match="16 KB"):
        tasks.submit("large", "save_note", {"text": "x" * 17000})


def test_approval_is_explicit_and_audited(tmp_path):
    engine = AutonomyEngine(tmp_path / "engine.sqlite3", auto_run_reversible=False)
    tasks = TaskLifecycle(engine, tmp_path / "lifecycle.sqlite3")
    task = tasks.submit("review note", "save_note", {"text": "approved text"})
    held = tasks.run_once()[0]
    assert held["status"] == "needs_approval"
    approved = tasks.approve(task["task_id"])
    assert approved["status"] == "queued"
    assert tasks.events(task["task_id"])[0]["event"] == "approved"


def test_approval_rejects_tasks_not_awaiting_review(tmp_path):
    engine = AutonomyEngine(tmp_path / "engine.sqlite3")
    tasks = TaskLifecycle(engine, tmp_path / "lifecycle.sqlite3")
    task = tasks.submit("ordinary note", "save_note", {"text": "hello"})
    with pytest.raises(ValueError, match="awaiting approval"):
        tasks.approve(task["task_id"])

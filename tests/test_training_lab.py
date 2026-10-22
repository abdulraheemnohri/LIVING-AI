import json
import pytest
from living_ai import training_lab

def test_upload_dataset_hash_dedup_and_manifest(tmp_path, monkeypatch):
    monkeypatch.setenv("LIVING_AI_DATA_DIR", str(tmp_path / "data"))
    item = training_lab.ingest_dataset("notes.txt", "Safe training corpus.", "manual")
    assert item["status"] == "available-for-training"
    assert item["sha256"]
    assert training_lab.list_datasets()[0]["id"] == item["id"]
    with pytest.raises(ValueError, match="Duplicate"):
        training_lab.ingest_dataset("another.txt", "Safe training corpus.", "manual")

def test_reject_unsupported_and_invalid_json(tmp_path, monkeypatch):
    monkeypatch.setenv("LIVING_AI_DATA_DIR", str(tmp_path / "data"))
    with pytest.raises(ValueError, match="Supported"):
        training_lab.ingest_dataset("payload.pdf", "not supported")
    with pytest.raises(ValueError, match="Invalid JSON"):
        training_lab.ingest_dataset("payload.json", "{bad")

def test_teacher_candidates_require_manual_approval(tmp_path, monkeypatch):
    monkeypatch.setenv("LIVING_AI_DATA_DIR", str(tmp_path / "data"))
    def fake_generate(prompt, max_new_tokens):
        assert "untrusted data" in prompt
        return "Candidate one\n---\nCandidate two"
    monkeypatch.setattr("living_ai.litert_lm_backend.generate", fake_generate)
    result = training_lab.prepare_teacher_corpus("Source facts.", 2)
    assert result["status"] == "pending-human-review"
    assert training_lab.training_history()[0]["status"] == "pending-human-review"
    approved = training_lab.approve_teacher_candidate(result["id"])
    assert approved["status"] == "human-approved"
    assert "Review it" in approved["note"]
    assert len(list((tmp_path / "data" / "training_lab" / "approved").glob("*.txt"))) == 1

def test_teacher_failure_does_not_create_candidates(tmp_path, monkeypatch):
    monkeypatch.setenv("LIVING_AI_DATA_DIR", str(tmp_path / "data"))
    def broken(*args, **kwargs):
        raise RuntimeError("runtime unavailable")
    monkeypatch.setattr("living_ai.litert_lm_backend.generate", broken)
    with pytest.raises(RuntimeError, match="no candidates created"):
        training_lab.prepare_teacher_corpus("Source facts.", 1)
    assert training_lab.training_history() == []

import pytest
from living_ai import db
from living_ai.evolution import create_proposal,evaluate,promote,rollback
def test_reversible_settings(tmp_path,monkeypatch):
    monkeypatch.setenv("LIVING_AI_DATA_DIR",str(tmp_path));db.init_db();before=db.get_settings()
    p=create_proposal("Test",{"retrieval_limit":7});evaluate(p["id"]);promote(p["id"])
    assert db.get_settings()["retrieval_limit"]==7
    rollback();assert db.get_settings()==before
def test_disallow_commands(tmp_path,monkeypatch):
    monkeypatch.setenv("LIVING_AI_DATA_DIR",str(tmp_path));db.init_db()
    with pytest.raises(ValueError):create_proposal("Bad",{"shell":"rm -rf"})

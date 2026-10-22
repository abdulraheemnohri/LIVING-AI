from living_ai import db
from living_ai.memory import add_memory,search_memories,delete_memory
def test_memory(tmp_path,monkeypatch):
    monkeypatch.setenv("LIVING_AI_DATA_DIR",str(tmp_path));db.init_db()
    m=add_memory("Project stores local SQLite memory","test")
    assert search_memories("SQLite")[0]["id"]==m["id"]
    assert delete_memory(m["id"]) and not search_memories("SQLite")

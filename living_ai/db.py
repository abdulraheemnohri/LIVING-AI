import json, os, sqlite3
from pathlib import Path
from datetime import datetime, timezone
from contextlib import contextmanager

def utcnow(): return datetime.now(timezone.utc).isoformat()
def data_dir():
    p=Path(os.getenv("LIVING_AI_DATA_DIR","./data")).expanduser()
    p.mkdir(parents=True,exist_ok=True); (p/"corpus").mkdir(exist_ok=True); return p
@contextmanager
def connect():
    c=sqlite3.connect(data_dir()/"living_ai.sqlite3",timeout=15); c.row_factory=sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    try: yield c; c.commit()
    finally: c.close()
def init_db():
    with connect() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS memories(id INTEGER PRIMARY KEY,content TEXT NOT NULL,source TEXT NOT NULL,created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS proposals(id INTEGER PRIMARY KEY,title TEXT,changes_json TEXT,status TEXT,evaluation_json TEXT,created_at TEXT,updated_at TEXT);
        CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value_json TEXT,updated_at TEXT);
        CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,action TEXT,detail_json TEXT,created_at TEXT);
        """)
        for k,v in {"temperature":0.7,"max_reply_chars":1800,"retrieval_limit":5}.items():
            c.execute("INSERT OR IGNORE INTO settings VALUES(?,?,?)",(k,json.dumps(v),utcnow()))
def audit(action,detail):
    # Tests and standalone services may call audit before application startup.
    init_db()
    with connect() as c: c.execute("INSERT INTO audit(action,detail_json,created_at) VALUES(?,?,?)",(action,json.dumps(detail),utcnow()))
def get_settings():
    with connect() as c: rows=c.execute("SELECT key,value_json FROM settings").fetchall()
    return {r["key"]:json.loads(r["value_json"]) for r in rows}
def set_settings(changes):
    with connect() as c:
        for k,v in changes.items():
            c.execute("INSERT INTO settings VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json,updated_at=excluded.updated_at",(k,json.dumps(v),utcnow()))

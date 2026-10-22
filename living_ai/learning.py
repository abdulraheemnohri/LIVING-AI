"""Local, auditable task outcome memory; no model training or action execution."""
from __future__ import annotations
import json, sqlite3, time, uuid
from pathlib import Path
from typing import Any

def _tokens(text: str) -> set[str]:
    return {word.lower() for word in text.split() if len(word) > 2}

class LearningStore:
    """SQLite store for evaluator/human feedback and lightweight lexical retrieval."""
    def __init__(self, db_path: str | Path = "data/learning.sqlite3") -> None:
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS evaluations (
                id TEXT PRIMARY KEY, goal TEXT NOT NULL, plan_summary TEXT NOT NULL,
                score REAL NOT NULL CHECK(score >= 0 AND score <= 1), outcome TEXT NOT NULL,
                feedback TEXT NOT NULL, tags_json TEXT NOT NULL, created_at REAL NOT NULL)""")
            db.execute("CREATE INDEX IF NOT EXISTS idx_evaluations_created ON evaluations(created_at DESC)")
    def _connect(self):
        db = sqlite3.connect(self.db_path, timeout=10)
        db.row_factory = sqlite3.Row
        return db
    def record(self, goal: str, *, score: float, outcome: str, feedback: str = "",
               plan_summary: str = "", tags: list[str] | None = None) -> dict[str, Any]:
        goal = " ".join(str(goal).split()); outcome = " ".join(str(outcome).split())
        feedback = str(feedback).strip(); plan_summary = str(plan_summary).strip()
        if not goal or len(goal) > 1000: raise ValueError("Goal must contain 1–1000 characters")
        if not isinstance(score, (int, float)) or isinstance(score, bool) or not 0 <= score <= 1:
            raise ValueError("Score must be a number from 0 to 1")
        if not outcome or len(outcome) > 2000 or len(feedback) > 4000 or len(plan_summary) > 4000:
            raise ValueError("Outcome is required; text fields exceed their limits")
        clean_tags = []
        for tag in (tags or [])[:20]:
            tag = " ".join(str(tag).split()).lower()
            if tag and len(tag) <= 40: clean_tags.append(tag)
        item = {"id":uuid.uuid4().hex,"goal":goal,"plan_summary":plan_summary,"score":float(score),
                "outcome":outcome,"feedback":feedback,"tags":clean_tags,"created_at":time.time()}
        with self._connect() as db:
            db.execute("INSERT INTO evaluations VALUES(?,?,?,?,?,?,?,?)",
                (item["id"],goal,plan_summary,item["score"],outcome,feedback,
                 json.dumps(clean_tags,ensure_ascii=False),item["created_at"]))
        return item
    def retrieve(self, query: str, *, limit: int = 5) -> list[dict[str, Any]]:
        limit=max(1,min(int(limit),20)); query_tokens=_tokens(str(query))
        with self._connect() as db:
            rows=db.execute("SELECT * FROM evaluations ORDER BY created_at DESC LIMIT 500").fetchall()
        ranked=[]
        for row in rows:
            item=dict(row); item["tags"]=json.loads(item.pop("tags_json"))
            searchable=" ".join([item["goal"],item["plan_summary"],item["outcome"],item["feedback"],*item["tags"]])
            overlap=len(query_tokens & _tokens(searchable))
            if overlap or not query_tokens:
                item["relevance"]=overlap/max(1,len(query_tokens)); ranked.append(item)
        ranked.sort(key=lambda x:(x["relevance"],x["created_at"]),reverse=True)
        return ranked[:limit]
    def summary(self) -> dict[str, Any]:
        with self._connect() as db:
            row=db.execute("SELECT COUNT(*) total, AVG(score) average_score, SUM(CASE WHEN score >= 0.7 THEN 1 ELSE 0 END) positive FROM evaluations").fetchone()
        return {"evaluations":int(row["total"] or 0),
                "average_score":round(float(row["average_score"]),4) if row["average_score"] is not None else None,
                "positive_evaluations":int(row["positive"] or 0)}

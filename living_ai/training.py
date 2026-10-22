from pathlib import Path
from .model import CharNGramModel
from .db import audit,init_db
def train_directory(input_dir="data/corpus",output="models/char_ngram.json"):
    init_db()
    source=Path(input_dir)
    if not source.is_dir(): raise ValueError(f"Input directory does not exist: {source}")
    docs=[p for p in source.rglob("*.txt") if p.is_file() and p.stat().st_size<=5_000_000]
    if not docs: raise ValueError(f"No .txt files found under {source}")
    model=CharNGramModel(4)
    for p in docs: model.train_text(p.read_text(encoding="utf-8",errors="replace"))
    model.save(output); result={"files":len(docs),"trained_chars":model.trained_chars,"output":str(output),"order":4}
    audit("model.train",result);return result

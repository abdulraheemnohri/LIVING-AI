from pathlib import Path
from .model import CharNGramModel
from .db import audit,init_db
from .knowledge import parse_document

def train_directory(input_dir="data/corpus",output="models/char_ngram.json"):
    init_db()
    source=Path(input_dir)
    if not source.is_dir(): raise ValueError(f"Input directory does not exist: {source}")
    docs=[p for p in source.rglob("*") if p.is_file() and p.suffix.lower() in {".txt",".md",".json"} and p.stat().st_size<=2_000_000]
    if not docs: raise ValueError(f"No .txt, .md or .json files (each <= 2 MB) found under {source}")
    model=CharNGramModel(4)
    used=0
    for p in sorted(docs):
        try: text=parse_document(p.name,p.read_text(encoding="utf-8",errors="replace"))
        except (OSError,ValueError): continue
        model.train_text(text);used+=1
    if not used: raise ValueError("No readable training documents found")
    model.save(output)
    result={"files":used,"trained_chars":model.trained_chars,"output":str(output),"order":4}
    audit("model.train",result)
    return result

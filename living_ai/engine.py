import os
from pathlib import Path
from .db import get_settings
from .memory import search_memories
from .model import CharNGramModel
def respond(message):
    message=message.strip()
    if not message: raise ValueError("Message cannot be empty")
    s=get_settings(); memories=search_memories(message,s.get("retrieval_limit",5))
    if memories:
        answer="Related local memory:\n"+"\n".join("- "+m["content"][:500] for m in memories)
        backend="local-memory-retrieval"
    else:
        path=Path(os.getenv("LIVING_AI_MODEL_PATH","models/char_ngram.json"))
        if path.exists():
            model=CharNGramModel.load(path);answer=model.generate(message+"\n",min(s["max_reply_chars"],800),s["temperature"]);backend="original-char-ngram"
        else:
            answer="I am LIVING AI in local starter mode. Save knowledge or train the original small character n-gram model. Stronger reasoning requires an optional model provider."
            backend="native-local"
    return {"answer":answer[:s["max_reply_chars"]],"backend":backend,"memories_used":len(memories)}

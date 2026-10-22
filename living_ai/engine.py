import os
from pathlib import Path

from .db import get_settings
from .memory import search_memories
from .model import CharNGramModel
from .providers import remote_chat


def respond(message):
    message = message.strip()
    if not message:
        raise ValueError("Message cannot be empty")
    settings = get_settings()
    memories = search_memories(message, settings.get("retrieval_limit", 5))
    backend = os.getenv("LIVING_AI_MODEL_BACKEND", "char_ngram").strip().lower()
    if backend in {"tiny_transformer", "from_scratch", "native_transformer"}:
        try:
            from .neural_lm import generate
            context = ""
            if memories:
                context = "Relevant saved notes:\n" + "\n".join("- " + item["content"][:400] for item in memories) + "\n\n"
            answer = generate(context + message, model_dir=os.getenv("LIVING_AI_TINY_MODEL_DIR", "models/tiny_transformer"), max_new_tokens=min(512, max(32, settings["max_reply_chars"] // 3)), temperature=settings["temperature"], device=os.getenv("LIVING_AI_TINY_DEVICE", "cpu"))
            return {"answer": answer[:settings["max_reply_chars"]], "backend": "from-scratch-tiny-transformer", "model": os.getenv("LIVING_AI_TINY_MODEL_DIR", "models/tiny_transformer"), "memories_used": len(memories)}
        except (RuntimeError, OSError, ValueError) as exc:
            return {"answer": f"From-scratch model could not load or generate: {exc}", "backend": "from-scratch-model-error", "memories_used": len(memories)}
    remote = remote_chat(message)
    if remote:
        return {"answer": remote[:settings["max_reply_chars"]], "backend": "optional-compatible-provider", "memories_used": len(memories)}
    if memories:
        answer = "Related local memory:\n" + "\n".join("- " + item["content"][:500] for item in memories)
        selected_backend = "local-memory-retrieval"
    else:
        path = Path(os.getenv("LIVING_AI_MODEL_PATH", "models/char_ngram.json"))
        if path.exists():
            model = CharNGramModel.load(path)
            answer = model.generate(message + "\n", min(settings["max_reply_chars"], 800), settings["temperature"])
            selected_backend = "original-char-ngram"
        else:
            answer = "I am LIVING AI in local starter mode. Train the character n-gram baseline, or train the from-scratch Transformer with python -m living_ai.train_neural. Set LIVING_AI_MODEL_BACKEND=tiny_transformer to use its checkpoint. LIVING AI's from-scratch model is the supported neural backend."
            selected_backend = "native-local"
    return {"answer": answer[:settings["max_reply_chars"]], "backend": selected_backend, "memories_used": len(memories)}

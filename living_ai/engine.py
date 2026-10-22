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

    if backend in {"transformers", "smollm3", "huggingface"}:
        try:
            from .hf_model import generate
            context = ""
            if memories:
                context = "Relevant saved notes:\n" + "\n".join(
                    "- " + item["content"][:500] for item in memories
                ) + "\n\n"
            answer = generate(
                context + message,
                max_new_tokens=min(512, max(32, settings["max_reply_chars"] // 3)),
                temperature=settings["temperature"],
            )
            return {
                "answer": answer[:settings["max_reply_chars"]],
                "backend": "huggingface-transformers",
                "model": os.getenv("LIVING_AI_HF_MODEL_ID", "HuggingFaceTB/SmolLM3-3B-Base"),
                "memories_used": len(memories),
            }
        except (RuntimeError, OSError, ValueError) as exc:
            return {
                "answer": f"Local Transformers model could not load or generate: {exc}",
                "backend": "huggingface-transformers-error",
                "model": os.getenv("LIVING_AI_HF_MODEL_ID", "HuggingFaceTB/SmolLM3-3B-Base"),
                "memories_used": len(memories),
            }

    remote = remote_chat(message)
    if remote:
        return {
            "answer": remote[:settings["max_reply_chars"]],
            "backend": "optional-compatible-provider",
            "memories_used": len(memories),
        }

    if memories:
        answer = "Related local memory:\n" + "\n".join(
            "- " + item["content"][:500] for item in memories
        )
        selected_backend = "local-memory-retrieval"
    else:
        path = Path(os.getenv("LIVING_AI_MODEL_PATH", "models/char_ngram.json"))
        if path.exists():
            model = CharNGramModel.load(path)
            answer = model.generate(
                message + "\n",
                min(settings["max_reply_chars"], 800),
                settings["temperature"],
            )
            selected_backend = "original-char-ngram"
        else:
            answer = (
                "I am LIVING AI in local starter mode. Save knowledge or train the "
                "original small character n-gram model. Set LIVING_AI_MODEL_BACKEND="
                "transformers to use SmolLM3-3B-Base if its optional dependencies and "
                "hardware requirements are available."
            )
            selected_backend = "native-local"
    return {
        "answer": answer[:settings["max_reply_chars"]],
        "backend": selected_backend,
        "memories_used": len(memories),
    }

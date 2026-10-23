import os
from pathlib import Path

from .db import get_settings
from .memory import search_memories
from .model import CharNGramModel
from .providers import remote_chat


def _memory_context(memories):
    if not memories:
        return ""
    return "Relevant saved notes:\n" + "\n".join(
        "- " + item["content"][:400] for item in memories
    ) + "\n\n"


def _litert_answer(prompt, settings):
    from .litert_lm_backend import generate
    max_tokens = min(512, max(32, settings["max_reply_chars"] // 3))
    return generate(prompt, max_new_tokens=max_tokens)


def _fallback_answer(message, memories, settings):
    if memories:
        answer = "Related local memory:\n" + "\n".join(
            "- " + item["content"][:500] for item in memories
        )
        return answer[:settings["max_reply_chars"]], "local-memory-retrieval"

    path = Path(os.getenv("LIVING_AI_MODEL_PATH", "models/char_ngram.json"))
    if path.exists():
        model = CharNGramModel.load(path)
        answer = model.generate(
            message + "\n",
            min(settings["max_reply_chars"], 800),
            settings["temperature"],
        )
        return answer[:settings["max_reply_chars"]], "original-char-ngram"

    return (
        "I am LIVING AI in local starter mode. Train the character n-gram baseline "
        "with python -m living_ai.train, or configure a local LiteRT-LM .litertlm "
        "model. Hybrid mode falls back to local memory or n-gram when LiteRT-LM "
        "is unavailable.",
        "native-local",
    )


def respond(message):
    message = message.strip()
    if not message:
        raise ValueError("Message cannot be empty")

    settings = get_settings()
    memories = search_memories(message, settings.get("retrieval_limit", 5))
    backend = os.getenv("LIVING_AI_MODEL_BACKEND", "char_ngram").strip().lower()
    allowed = {
        "char_ngram", "tiny_transformer", "from_scratch", "native_transformer",
        "litert_lm", "hybrid",
    }
    if backend not in allowed:
        backend = "char_ngram"

    if backend in {"litert_lm", "hybrid"}:
        prompt = (
            "You are LIVING AI, a helpful local assistant. Use the relevant saved "
            "notes as context when useful. If the notes do not answer the question, "
            "say what you know and do not invent facts.\n\n"
            + _memory_context(memories)
            + "User: " + message + "\nAssistant:"
        )
        try:
            answer = _litert_answer(prompt, settings)
            return {
                "answer": answer[:settings["max_reply_chars"]],
                "backend": "litert-lm",
                "model": os.getenv(
                    "LIVING_AI_LITERTLM_MODEL_PATH",
                    "models/litert/model.litertlm",
                ),
                "memories_used": len(memories),
                "fallback": False,
            }
        except (ImportError, RuntimeError, OSError, ValueError) as exc:
            if backend == "litert_lm":
                return {
                    "answer": (
                        f"LiteRT-LM could not run: {exc}. In hybrid mode the app "
                        "would fall back to the local baseline."
                    )[:settings["max_reply_chars"]],
                    "backend": "litert-lm-error",
                    "memories_used": len(memories),
                    "fallback": False,
                }
            answer, selected_backend = _fallback_answer(message, memories, settings)
            return {
                "answer": answer,
                "backend": selected_backend,
                "memories_used": len(memories),
                "fallback": True,
                "fallback_reason": str(exc)[:300],
            }

    if backend in {"tiny_transformer", "from_scratch", "native_transformer"}:
        try:
            from .neural_lm import generate
            answer = generate(
                _memory_context(memories) + message,
                model_dir=os.getenv("LIVING_AI_TINY_MODEL_DIR", "models/tiny_transformer"),
                max_new_tokens=min(512, max(32, settings["max_reply_chars"] // 3)),
                temperature=settings["temperature"],
                device=os.getenv("LIVING_AI_TINY_DEVICE", "cpu"),
            )
            return {
                "answer": answer[:settings["max_reply_chars"]],
                "backend": "from-scratch-tiny-transformer",
                "model": os.getenv("LIVING_AI_TINY_MODEL_DIR", "models/tiny_transformer"),
                "memories_used": len(memories),
            }
        except (RuntimeError, OSError, ValueError) as exc:
            return {
                "answer": f"From-scratch model could not load or generate: {exc}",
                "backend": "from-scratch-model-error",
                "memories_used": len(memories),
            }

    remote = remote_chat(message)
    if remote:
        return {
            "answer": remote[:settings["max_reply_chars"]],
            "backend": "optional-compatible-provider",
            "memories_used": len(memories),
        }

    answer, selected_backend = _fallback_answer(message, memories, settings)
    return {
        "answer": answer[:settings["max_reply_chars"]],
        "backend": selected_backend,
        "memories_used": len(memories),
    }

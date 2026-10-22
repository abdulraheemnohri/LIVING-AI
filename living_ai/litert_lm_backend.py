"""Optional LiteRT-LM adapter. Keeps the lightweight n-gram model as a fallback."""
from __future__ import annotations

import os
from pathlib import Path


def is_configured() -> bool:
    model_path = Path(os.getenv("LIVING_AI_LITERTLM_MODEL_PATH", "models/litert/gemma-4-E2B-it.litertlm")).expanduser()
    return model_path.is_file()


def generate(prompt: str, max_new_tokens: int = 256) -> str:
    """Generate a response using the official LiteRT-LM Python API.

    The engine is scoped to one request so model resources are released reliably.
    This is conservative but can reload the model for each request; a persistent
    engine manager can be added later after Android memory/architecture testing.
    """
    model_path = Path(os.getenv("LIVING_AI_LITERTLM_MODEL_PATH", "models/litert/gemma-4-E2B-it.litertlm")).expanduser()
    if not model_path.is_file():
        raise FileNotFoundError(f"LiteRT-LM model not found: {model_path}")

    try:
        import litert_lm
    except ImportError as exc:
        raise RuntimeError(
            "LiteRT-LM Python API is not installed. Install the optional dependency "
            "with: python -m pip install -e '.[litert]'"
        ) from exc

    backend_name = os.getenv("LIVING_AI_LITERTLM_BACKEND", "cpu").strip().lower()
    backend = None
    if backend_name == "gpu":
        backend = litert_lm.Backend.GPU()
    elif backend_name == "npu":
        backend = litert_lm.Backend.NPU()
    elif backend_name != "cpu":
        raise ValueError("LIVING_AI_LITERTLM_BACKEND must be cpu, gpu, or npu")

    engine_args = {"backend": backend} if backend is not None else {}
    pieces: list[str] = []
    with litert_lm.Engine(str(model_path), **engine_args) as engine:
        with engine.create_conversation(max_output_tokens=max(1, min(4096, int(max_new_tokens)))) as conversation:
            for chunk in conversation.send_message_async(prompt):
                for item in chunk.get("content", []):
                    text = item.get("text")
                    if isinstance(text, str):
                        pieces.append(text)
    answer = "".join(pieces).strip()
    if not answer:
        raise RuntimeError("LiteRT-LM returned an empty response")
    return answer

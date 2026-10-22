"""Optional Hugging Face Transformers inference for SmolLM3-3B-Base.

This module is imported only when LIVING_AI_MODEL_BACKEND=transformers.
The base checkpoint is a pretrained continuation model, not the instruction-tuned
SmolLM3 chat checkpoint, so prompting quality may be less conversational.
"""
from __future__ import annotations

import os
from functools import lru_cache


DEFAULT_MODEL_ID = "HuggingFaceTB/SmolLM3-3B-Base"


@lru_cache(maxsize=1)
def _load_model():
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as exc:
        raise RuntimeError(
            "Transformers backend dependencies are missing. Install with: "
            "python -m pip install -e '.[hf]'"
        ) from exc

    model_id = os.getenv("LIVING_AI_HF_MODEL_ID", DEFAULT_MODEL_ID).strip() or DEFAULT_MODEL_ID
    cache_dir = os.getenv("LIVING_AI_HF_CACHE", "").strip() or None
    local_only = os.getenv("LIVING_AI_HF_LOCAL_ONLY", "false").lower() == "true"
    tokenizer = AutoTokenizer.from_pretrained(
        model_id, cache_dir=cache_dir, local_files_only=local_only
    )
    # CPU is the safe default for a Debian userspace on Android. Do not assume CUDA.
    device = os.getenv("LIVING_AI_HF_DEVICE", "cpu").strip().lower()
    dtype_name = os.getenv("LIVING_AI_HF_DTYPE", "auto").strip().lower()
    kwargs = {"cache_dir": cache_dir, "local_files_only": local_only}
    if dtype_name == "float32":
        kwargs["torch_dtype"] = torch.float32
    elif dtype_name == "bfloat16":
        kwargs["torch_dtype"] = torch.bfloat16
    elif dtype_name == "float16":
        kwargs["torch_dtype"] = torch.float16
    # "auto" lets Transformers use checkpoint dtype where supported.
    model = AutoModelForCausalLM.from_pretrained(model_id, **kwargs)
    if device != "auto":
        model = model.to(device)
    model.eval()
    return tokenizer, model, torch, model_id


def generate(prompt: str, max_new_tokens: int = 160, temperature: float = 0.7) -> str:
    tokenizer, model, torch, model_id = _load_model()
    system = (
        "Continue the following assistant response helpfully, accurately, and concisely. "
        "If the request is ambiguous, state your assumption.\n\n"
    )
    # Base models are trained to continue text; do not assume a chat template exists.
    text = f"{system}User: {prompt.strip()}\nAssistant:"
    inputs = tokenizer(text, return_tensors="pt")
    try:
        device = next(model.parameters()).device
        inputs = {key: value.to(device) for key, value in inputs.items()}
    except StopIteration:
        pass
    kwargs = {
        "max_new_tokens": max(1, min(int(max_new_tokens), 512)),
        "pad_token_id": tokenizer.eos_token_id,
        "do_sample": float(temperature) > 0,
    }
    if kwargs["do_sample"]:
        kwargs["temperature"] = max(0.05, min(float(temperature), 2.0))
        kwargs["top_p"] = 0.9
    with torch.inference_mode():
        output = model.generate(**inputs, **kwargs)
    new_tokens = output[0, inputs["input_ids"].shape[1]:]
    answer = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
    # Stop if the base model begins inventing a new dialogue turn.
    for marker in ("\nUser:", "\nHuman:", "\n### User"):
        if marker in answer:
            answer = answer.split(marker, 1)[0].strip()
    if not answer:
        answer = f"The model ({model_id}) returned an empty continuation. Try a different prompt."
    return answer

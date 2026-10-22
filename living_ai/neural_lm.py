"""Small byte-level causal Transformer trained from scratch with PyTorch.

The model uses UTF-8 bytes rather than a pretrained tokenizer, so it can represent
English, Urdu, and other Unicode text without downloading vocabulary assets. It is
a toy research model: useful for learning and local experiments, not comparable to
a pretrained assistant. PyTorch is imported lazily because it is optional.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

FORMAT_VERSION = 1
SPECIAL_TOKENS = 3  # PAD=0, BOS=1, EOS=2
VOCAB_SIZE = 256 + SPECIAL_TOKENS


def encode_text(text: str, add_bos: bool = True, add_eos: bool = True) -> list[int]:
    ids = list(text.encode("utf-8", errors="replace"))
    return ([1] if add_bos else []) + [b + SPECIAL_TOKENS for b in ids] + ([2] if add_eos else [])


def decode_tokens(ids: list[int]) -> str:
    data = bytearray()
    for token in ids:
        if SPECIAL_TOKENS <= int(token) < VOCAB_SIZE:
            data.append(int(token) - SPECIAL_TOKENS)
    return data.decode("utf-8", errors="replace")


def default_config() -> dict:
    return {
        "format_version": FORMAT_VERSION,
        "vocab_size": VOCAB_SIZE,
        "block_size": int(os.getenv("LIVING_AI_TINY_BLOCK_SIZE", "128")),
        "d_model": int(os.getenv("LIVING_AI_TINY_D_MODEL", "128")),
        "n_heads": int(os.getenv("LIVING_AI_TINY_HEADS", "4")),
        "n_layers": int(os.getenv("LIVING_AI_TINY_LAYERS", "2")),
        "dropout": float(os.getenv("LIVING_AI_TINY_DROPOUT", "0.1")),
    }


def validate_config(config: dict) -> dict:
    cfg = dict(config)
    if cfg.get("format_version") != FORMAT_VERSION:
        raise ValueError("Unsupported tiny model format")
    if cfg.get("vocab_size") != VOCAB_SIZE:
        raise ValueError("Unexpected vocabulary size")
    block = int(cfg.get("block_size", 0))
    width = int(cfg.get("d_model", 0))
    heads = int(cfg.get("n_heads", 0))
    layers = int(cfg.get("n_layers", 0))
    if not 16 <= block <= 2048:
        raise ValueError("block_size must be between 16 and 2048")
    if not 32 <= width <= 1024 or width % max(1, heads):
        raise ValueError("d_model must be 32..1024 and divisible by n_heads")
    if not 1 <= heads <= 16 or not 1 <= layers <= 12:
        raise ValueError("n_heads must be 1..16 and n_layers must be 1..12")
    if not 0.0 <= float(cfg.get("dropout", 0.1)) < 1.0:
        raise ValueError("dropout must be in [0, 1)")
    return cfg


def _torch():
    try:
        import torch
        from torch import nn
    except ImportError as exc:
        raise RuntimeError("The from-scratch Transformer requires PyTorch. Install a compatible torch build for this Debian/Android architecture.") from exc
    return torch, nn


def create_model(config: dict):
    torch, nn = _torch()
    cfg = validate_config(config)

    class CausalBlock(nn.Module):
        def __init__(self):
            super().__init__()
            self.norm1 = nn.LayerNorm(cfg["d_model"])
            self.attn = nn.MultiheadAttention(
                cfg["d_model"], cfg["n_heads"], dropout=cfg["dropout"], batch_first=True
            )
            self.norm2 = nn.LayerNorm(cfg["d_model"])
            self.ff = nn.Sequential(
                nn.Linear(cfg["d_model"], 4 * cfg["d_model"]),
                nn.GELU(),
                nn.Linear(4 * cfg["d_model"], cfg["d_model"]),
                nn.Dropout(cfg["dropout"]),
            )

        def forward(self, x, mask):
            y = self.norm1(x)
            x = x + self.attn(y, y, y, attn_mask=mask, need_weights=False)[0]
            return x + self.ff(self.norm2(x))

    class TinyCausalLM(nn.Module):
        def __init__(self):
            super().__init__()
            self.token = nn.Embedding(cfg["vocab_size"], cfg["d_model"])
            self.position = nn.Embedding(cfg["block_size"], cfg["d_model"])
            self.blocks = nn.ModuleList([CausalBlock() for _ in range(cfg["n_layers"])])
            self.norm = nn.LayerNorm(cfg["d_model"])
            self.head = nn.Linear(cfg["d_model"], cfg["vocab_size"], bias=False)
            self.head.weight = self.token.weight

        def forward(self, ids):
            length = ids.shape[1]
            positions = torch.arange(length, device=ids.device)
            x = self.token(ids) + self.position(positions)[None, :, :]
            mask = torch.triu(torch.ones(length, length, device=ids.device, dtype=torch.bool), diagonal=1)
            for block in self.blocks:
                x = block(x, mask)
            return self.head(self.norm(x))

    return TinyCausalLM()


def load_model(model_dir: str | Path, device: str = "cpu"):
    torch, _ = _torch()
    path = Path(model_dir)
    config = validate_config(json.loads((path / "config.json").read_text(encoding="utf-8")))
    model = create_model(config)
    weights = path / "weights.pt"
    if not weights.is_file():
        raise FileNotFoundError(f"Missing model weights: {weights}")
    # weights.pt is a local artifact produced by this project's trainer. Never load
    # checkpoints downloaded from unknown sources.
    state = torch.load(weights, map_location=device, weights_only=True)
    model.load_state_dict(state)
    model.to(device).eval()
    return model, config


def generate(prompt: str, model_dir: str | Path = "models/tiny_transformer",
             max_new_tokens: int = 160, temperature: float = 0.8, device: str = "cpu") -> str:
    torch, _ = _torch()
    model, config = load_model(model_dir, device)
    ids = encode_text(prompt, add_bos=True, add_eos=False)
    context = torch.tensor([ids[-config["block_size"]:]], dtype=torch.long, device=device)
    result = list(ids)
    limit = max(1, min(int(max_new_tokens), 1024))
    temp = max(0.05, min(float(temperature), 2.0))
    with torch.inference_mode():
        for _ in range(limit):
            logits = model(context)[:, -1, :] / temp
            logits[:, :SPECIAL_TOKENS] = -float("inf")
            token = int(torch.multinomial(torch.softmax(logits, dim=-1), num_samples=1).item())
            if token == 2:
                break
            result.append(token)
            next_ids = torch.cat([context, torch.tensor([[token]], device=device)], dim=1)
            context = next_ids[:, -config["block_size"]:]
    return decode_tokens(result[len(ids):]).strip()

"""Training pipeline for LIVING AI's small from-scratch byte Transformer."""
from __future__ import annotations
import json
import random
from pathlib import Path
from .db import audit, init_db
from .knowledge import parse_document
from .neural_lm import create_model, default_config, encode_text, validate_config

def collect_text(input_dir: str | Path, max_file_bytes: int = 2_000_000) -> tuple[str, int]:
    root = Path(input_dir)
    if not root.is_dir():
        raise ValueError(f"Input directory does not exist: {root}")
    files = [p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in {".txt", ".md", ".json"} and p.stat().st_size <= max_file_bytes]
    if not files:
        raise ValueError(f"No .txt, .md or .json files (each <= {max_file_bytes} bytes) found under {root}")
    texts = []
    for path in sorted(files):
        try:
            raw = path.read_text(encoding="utf-8", errors="replace")
            text = parse_document(path.name, raw)
            if text:
                texts.append(text)
        except (OSError, ValueError):
            continue
    corpus = "\n\n".join(texts)
    if len(corpus.encode("utf-8")) < 64:
        raise ValueError("Corpus is too small or contains no readable documents; provide at least 64 UTF-8 bytes")
    return corpus, len(texts)

def train_small_transformer(input_dir: str = "data/corpus", output_dir: str = "models/tiny_transformer",
                            steps: int = 500, batch_size: int = 8, learning_rate: float = 3e-4,
                            seed: int = 42, config_overrides: dict | None = None) -> dict:
    try:
        import torch
        import torch.nn.functional as F
    except ImportError as exc:
        raise RuntimeError("Training from scratch requires PyTorch. Install a compatible torch build first.") from exc
    if not 1 <= int(steps) <= 100000: raise ValueError("steps must be between 1 and 100000")
    if not 1 <= int(batch_size) <= 128: raise ValueError("batch_size must be between 1 and 128")
    if not 1e-6 <= float(learning_rate) <= 0.1: raise ValueError("learning_rate must be between 1e-6 and 0.1")
    corpus, file_count = collect_text(input_dir)
    ids = encode_text(corpus)
    config = default_config()
    if config_overrides: config.update(config_overrides)
    config = validate_config(config)
    if len(ids) < config["block_size"] + 2:
        config["block_size"] = max(16, min(config["block_size"], len(ids) - 2))
    if len(ids) < config["block_size"] + 2: raise ValueError("Corpus is too short for the configured block_size")
    random.seed(seed); torch.manual_seed(seed)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = create_model(config).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=float(learning_rate))
    tensor = torch.tensor(ids, dtype=torch.long, device=device)
    block = config["block_size"]; losses=[]; model.train()
    for _ in range(int(steps)):
        starts = torch.randint(0, len(tensor) - block - 1, (int(batch_size),), device=device)
        x = torch.stack([tensor[int(i):int(i) + block] for i in starts])
        y = torch.stack([tensor[int(i) + 1:int(i) + block + 1] for i in starts])
        logits = model(x)
        loss = F.cross_entropy(logits.reshape(-1, config["vocab_size"]), y.reshape(-1))
        optimizer.zero_grad(set_to_none=True); loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0); optimizer.step()
        losses.append(float(loss.detach().cpu()))
    model.eval()
    target=Path(output_dir);target.mkdir(parents=True,exist_ok=True)
    weights_tmp=target/"weights.pt.tmp";torch.save(model.cpu().state_dict(),weights_tmp);weights_tmp.replace(target/"weights.pt")
    config["training"]={"source_files":file_count,"corpus_bytes":len(corpus.encode("utf-8")),"steps":int(steps),
      "batch_size":int(batch_size),"learning_rate":float(learning_rate),"seed":int(seed),"device":device,
      "final_loss":losses[-1],"parameters":sum(p.numel() for p in model.parameters())}
    config_tmp=target/"config.json.tmp";config_tmp.write_text(json.dumps(config,ensure_ascii=False,indent=2),encoding="utf-8");config_tmp.replace(target/"config.json")
    result={"output_dir":str(target),"source_files":file_count,"corpus_bytes":len(corpus.encode("utf-8")),"steps":int(steps),
      "final_loss":round(losses[-1],4),"initial_loss":round(losses[0],4),"parameters":config["training"]["parameters"],
      "device":device,"note":"Model initialized randomly and trained from scratch; quality depends on corpus and compute."}
    init_db();audit("model.train_from_scratch",result);return result

# LIVING-AI — Evolution Engine

A local-first AI workbench for Android Debian/Linux terminal environments. It combines persistent SQLite memory, an original trainable character n-gram baseline, optional local Hugging Face Transformers inference using **HuggingFaceTB/SmolLM3-3B-Base**, an optional OpenAI-compatible endpoint, and a reversible evolution engine.

> This is an evolving engineering project, not a claim of consciousness or frontier-level intelligence. SmolLM3-3B-Base is a pretrained base checkpoint and may not follow instructions as reliably as an instruction-tuned model. The built-in n-gram model remains the lightweight default.

## Quick start (Debian/Linux on Android)

```bash
git clone https://github.com/abdulraheemnohri/LIVING-AI.git
cd LIVING-AI
bash scripts/install_android_debian.sh
source .venv/bin/activate
bash scripts/run.sh
```

Open http://127.0.0.1:8000 in a browser. The server binds to localhost by default.

## Enable SmolLM3-3B-Base locally

Install the optional dependencies:

```bash
source .venv/bin/activate
python -m pip install -e '.[hf]'
export LIVING_AI_MODEL_BACKEND=transformers
export LIVING_AI_HF_MODEL_ID=HuggingFaceTB/SmolLM3-3B-Base
export LIVING_AI_HF_DEVICE=cpu
bash scripts/run.sh
```

The first chat request downloads the model if it is not cached. The 3B checkpoint is large; FP32 parameters alone can occupy around 12 GB, before runtime overhead. Many Android devices cannot load it in available RAM, and compatible PyTorch wheels may not exist for every Android Debian architecture. If install or loading fails, use the lightweight default or a compatible inference endpoint. See [docs/SMOLLM3.md](docs/SMOLLM3.md).

## Core capabilities

- Litestar API and responsive dashboard
- SQLite-backed persistent memory and lexical retrieval
- Original character n-gram model trained from local UTF-8 text
- Optional local SmolLM3-3B-Base inference via Transformers
- Optional OpenAI-compatible chat-completions provider (opt-in)
- Allowlisted settings evolution with evaluation, snapshots, audit trail, and rollback
- Local installation scripts and unit tests

## Train the original baseline

Place permitted plain-text files in `data/corpus/`, then use **Training Lab → Train model now**, or run:

```bash
python -m living_ai.train --input data/corpus --output models/char_ngram.json
```

This trains the small character n-gram baseline, not the SmolLM3 transformer. Fine-tuning a 3B transformer is a separate compute-intensive workflow; it is not performed by this command.

## Optional remote provider

Set `LIVING_AI_ALLOW_REMOTE_PROVIDER=true`, `LIVING_AI_PROVIDER_URL`, `LIVING_AI_PROVIDER_MODEL`, and optionally `LIVING_AI_PROVIDER_API_KEY`. When enabled, chat text is sent to that configured endpoint. Keep secrets out of source control.

## Safety and evolution

The evolution engine can only change the explicitly allowlisted settings `temperature`, `max_reply_chars`, and `retrieval_limit`. Changes are validated, snapshotted, and audited. It does not execute arbitrary shell commands, install packages, or rewrite its own Python source. Automatic promotion is opt-in through `LIVING_AI_AUTO_PROMOTE=true`.

Before exposing the server on a network, set `LIVING_AI_ADMIN_TOKEN` and review [SECURITY.md](SECURITY.md). Data lives under `LIVING_AI_DATA_DIR` (default `./data`).

## Development

```bash
python -m pip install -e '.[dev]'
python -m pytest
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), [docs/ANDROID_DEBIAN.md](docs/ANDROID_DEBIAN.md), and [docs/SMOLLM3.md](docs/SMOLLM3.md).

## Current limitations

- SmolLM3-3B-Base is a base model, not instruction-tuned, and can produce weak or incoherent continuations.
- Model loading may exceed Android device RAM; PyTorch wheel support depends on architecture.
- No unattended web crawler is enabled; knowledge ingestion is explicit.
- App source-code self-updates and arbitrary code execution are intentionally excluded.
- Android CPU, RAM, storage, and thermal limits constrain inference and training.

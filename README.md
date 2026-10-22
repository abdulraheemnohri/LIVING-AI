# LIVING-AI — Evolution Engine

A local-first AI workbench for Android Debian/Linux terminal environments. The project combines persistent SQLite memory, an original trainable character n-gram model, an optional OpenAI-compatible model endpoint, and a reversible evolution engine.

> This is an evolving engineering project, not a claim of consciousness or frontier-level intelligence. The built-in model is a small baseline; stronger reasoning requires a separately configured model backend.

## Quick start (Debian/Linux on Android)

```bash
git clone https://github.com/abdulraheemnohri/LIVING-AI.git
cd LIVING-AI
bash scripts/install_android_debian.sh
source .venv/bin/activate
bash scripts/run.sh
```

Open http://127.0.0.1:8000 in a browser. The server binds to localhost by default.

## Core capabilities

- Litestar API and responsive dashboard
- SQLite-backed persistent memory and lexical retrieval
- Original character n-gram model trained from local UTF-8 text
- Optional OpenAI-compatible chat-completions provider (opt-in)
- Allowlisted settings evolution with evaluation, snapshots, audit trail, and rollback
- Local installation scripts and unit tests

## Train the original model

Place permitted plain-text files in `data/corpus/`, then use **Training Lab → Train model now**, or run:

```bash
python -m living_ai.train --input data/corpus --output models/char_ngram.json
```

This model is a character n-gram baseline, not a transformer LLM. Neural training requires additional dependencies and more compute.

## Optional model provider

Set `LIVING_AI_ALLOW_REMOTE_PROVIDER=true`, `LIVING_AI_PROVIDER_URL`, `LIVING_AI_PROVIDER_MODEL`, and optionally `LIVING_AI_PROVIDER_API_KEY`. When enabled, chat text is sent to that configured endpoint. Keep secrets out of source control.

## Safety and evolution

The evolution engine can only change the explicitly allowlisted settings `temperature`, `max_reply_chars`, and `retrieval_limit`. Changes are validated, snapshotted, and audited. It does not execute arbitrary shell commands, install packages, or rewrite its own Python source. Automatic promotion is opt-in through `LIVING_AI_AUTO_PROMOTE=true`.

Before exposing the server on a network, set `LIVING_AI_ADMIN_TOKEN` and review [SECURITY.md](SECURITY.md). Data lives under `LIVING_AI_DATA_DIR` (default `./data`).

## Development

```bash
python -m pip install -e ".[dev]"
python -m pytest
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and [docs/ANDROID_DEBIAN.md](docs/ANDROID_DEBIAN.md).

## Current limitations

- Built-in character n-gram model has limited language and reasoning ability.
- No unattended web crawler is enabled; knowledge ingestion is explicit.
- App source-code self-updates and arbitrary code execution are intentionally excluded.
- Android CPU, RAM, storage, and thermal limits constrain training.

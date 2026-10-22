# LIVING-AI — Evolution Engine

A local-first AI workbench for Android Debian/Linux terminal environments. It combines persistent SQLite memory, a character n-gram baseline, an original tiny byte-level Transformer trained from random initialization, optional LiteRT-LM inference, mobile file and public webpage knowledge import, an optional OpenAI-compatible endpoint, and reversible settings evolution.

> This is an evolving engineering project, not a claim of consciousness or frontier-level intelligence. The n-gram model is a lightweight fallback; LiteRT-LM requires a compatible pre-converted `.litertlm` model.

## Quick start (Debian/Linux on Android)

```bash
git clone https://github.com/abdulraheemnohri/LIVING-AI.git
cd LIVING-AI
bash scripts/install_android_debian.sh
source .venv/bin/activate
bash scripts/run.sh
```

Open http://127.0.0.1:8000 in a browser. The server binds to localhost by default.

## Hybrid inference: Character n-gram + LiteRT-LM

LIVING AI supports two complementary local engines:

- **Character n-gram:** very small resource footprint; learns character-level patterns from your corpus. It is not a modern reasoning LLM.
- **LiteRT-LM:** runs a compatible pre-converted `.litertlm` language model locally. Model quality and RAM requirements depend on the selected model and device.
- **Hybrid mode:** tries LiteRT-LM first, then falls back to saved local memory or the trained n-gram baseline if LiteRT-LM is unavailable or fails.

Install the optional Python API in the active virtual environment:

```bash
python -m pip install -e '.[litert]'
mkdir -p models/litert
```

Copy a legally obtained, compatible model file to `models/litert/model.litertlm`, or set `LIVING_AI_LITERTLM_MODEL_PATH` to its actual path. Start with CPU mode; GPU/NPU require supported runtime and hardware.

Set these values in your `.env` file:

```dotenv
LIVING_AI_MODEL_BACKEND=hybrid
LIVING_AI_LITERTLM_MODEL_PATH=models/litert/model.litertlm
LIVING_AI_LITERTLM_BACKEND=cpu
LIVING_AI_MODEL_PATH=models/char_ngram.json
```

Supported `LIVING_AI_MODEL_BACKEND` values are `hybrid`, `litert_lm`, `char_ngram`, and the existing `tiny_transformer` backend aliases. In strict `litert_lm` mode, a load/generation error is reported. In `hybrid` mode, the app records a fallback response and reason in the chat API result. The app does not download a model automatically.

Official LiteRT-LM docs:
- Python API: https://developers.google.com/edge/litert-lm/python
- CLI and model running: https://developers.google.com/edge/litert-lm/cli/usage

## Train a small language model from scratch

Install a compatible PyTorch build and run:

    python -m pip install -e '.[neural]'
    mkdir -p data/corpus
    python -m living_ai.train_neural --input data/corpus --steps 300 --batch-size 2 --width 64 --heads 4 --layers 2 --block-size 64

Or run the low-resource helper: `bash scripts/train_from_scratch_android.sh`.

Put lawful UTF-8 .txt, .md or .json files in data/corpus first. This creates a tiny byte-level causal Transformer with random initial weights. It can encode Urdu and other Unicode scripts, but byte-level learning is inefficient and a small dataset will usually produce weak, repetitive text. Training can be slow and heat a phone. Start with width 32–64, two layers, block size 32–64, and a few hundred steps. PyTorch wheels may not be available for every Android Debian architecture.

To serve the trained checkpoint, set LIVING_AI_MODEL_BACKEND=tiny_transformer and LIVING_AI_TINY_MODEL_DIR=models/tiny_transformer in .env, then restart. The dashboard Training page also includes the from-scratch trainer.

See docs/TRAIN_FROM_SCRATCH.md for details.

## Import data from your phone

Open **Import Data** in the dashboard. Select local `.txt`, `.md`, or `.json` files (up to 2 MB each), or paste a public webpage URL. JSON is validated; imported text is chunked into SQLite memory. The online importer limits pages to 1 MB, checks for public IP addresses, blocks redirects and accepts text content only. Sites that require login or JavaScript are not supported.

Imported knowledge is searchable memory; it does not automatically train the model. Use **Export saved memory to training corpus** on the Import Data page to prepare imported files and webpages for training. Then train from `data/corpus/`.

## Core capabilities

- Litestar API and responsive dashboard
- SQLite-backed persistent memory and lexical retrieval
- Original character n-gram baseline and from-scratch byte-level Transformer trained from local UTF-8 text
- Optional LiteRT-LM inference adapter with hybrid fallback
- Mobile file import for TXT, Markdown and JSON plus explicit public webpage import
- Optional OpenAI-compatible chat-completions provider (opt-in)
- Allowlisted settings evolution with evaluation, snapshots, audit trail, and rollback
- Local installation scripts and unit tests

## Train the original baseline

Place permitted plain-text files in `data/corpus/`, then use **Training Lab → Train model now**, or run:

```bash
python -m living_ai.train --input data/corpus --output models/char_ngram.json
```

This trains the small character n-gram baseline. The from-scratch Transformer has a separate training command; no pretrained model is included in the repository.

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

See `docs/ARCHITECTURE.md` and `docs/ANDROID_DEBIAN.md`.

## Current limitations

- The tiny from-scratch model is educational, not assistant-grade; training may be slow and PyTorch wheel support depends on architecture.
- LiteRT-LM requires a compatible external `.litertlm` model and installed runtime; model memory needs may exceed what a phone can spare.
- No unattended crawler, PDF/YouTube ingestion, transformer fine-tuning, automatic online training, or autonomous source-code self-update is implemented; web import is user-initiated.
- App source-code self-updates and arbitrary code execution are intentionally excluded.
- Android CPU, RAM, storage, and thermal limits constrain inference and training.

**Pretrained model removal:** The SmolLM3-3B-Base / Hugging Face Transformers backend has been removed. The default install does not include Transformers.

## Bounded autonomy engine

The optional `living_ai.autonomous.AutonomyEngine` adds a persistent goal queue, bounded execution cycles, a registered-action policy, reversible-action auto-run, approval holding, saved notes, and an auditable run history. It uses only the Python standard library and does not launch shell commands or rewrite source code.

See [docs/AUTONOMY.md](docs/AUTONOMY.md). Run the tests with `python -m pytest`. This is a controlled foundation: it does not start a background daemon automatically, and unknown or non-reversible actions are held instead of executed.

## Opt-in autonomy scheduler

`living_ai.scheduler.AutonomyScheduler` adds explicit pause/resume, interval-based cycle gating, disable/enable controls, status reporting, and a per-run cycle budget. It never starts itself, creates a background thread, or bypasses the autonomy engine's action policy.

See [docs/SCHEDULER.md](docs/SCHEDULER.md). Tests are in `tests/test_scheduler.py`.

## Goal planner (Phase 3 foundation)

`living_ai.planner.GoalPlanner` creates bounded, inspectable goal proposals and queues them for review without executing them. The baseline planner is deterministic and conservative; it does not call a model or access the network. See [docs/PLANNER.md](docs/PLANNER.md).

## Cognitive Core (Phase 4 foundation)

Optional model-assisted goal decomposition is available through `living_ai.cognitive.CognitiveCore`. Remote planning is opt-in, validates model output, restricts suggestions to short text items, and falls back to the deterministic planner on invalid or unavailable responses. Plans remain review-only. See [docs/COGNITIVE_CORE.md](docs/COGNITIVE_CORE.md).

## Learning and evaluation memory (Phase 5 foundation)

The optional `living_ai.learning.LearningStore` records reviewed outcomes and scores in local SQLite, retrieves similar prior evaluations using lightweight lexical overlap, and summarizes score trends. It does not independently verify success or modify model weights. See [docs/LEARNING.md](docs/LEARNING.md).

## Review-first evolution coordinator (Phase 6)

The `living_ai.coordinator.EvolutionCoordinator` connects the planner, optional cognitive adapter, SQLite evaluation memory, and persistent autonomy queue. `prepare()` returns a plan alongside relevant past evaluations without queueing or executing it; `submit_for_review()` queues proposals only; and `record_evaluation()` stores feedback provided by a caller or human reviewer. Prior evaluations are shown as context and are not injected into model prompts. Remote planning remains opt-in, and the autonomy engine's registered-action policy remains the execution gate.

See [docs/EVOLUTION_LOOP.md](docs/EVOLUTION_LOOP.md). Tests are in `tests/test_coordinator.py`.

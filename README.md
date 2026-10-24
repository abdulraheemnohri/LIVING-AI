# LIVING-AI — Evolution Engine

A local-first AI workbench for Android Debian/Linux terminal environments. It combines persistent SQLite memory, a character n-gram baseline, an original tiny byte-level Transformer trained from random initialization, optional LiteRT-LM inference, mobile file and public webpage knowledge import, an optional OpenAI-compatible endpoint, and reversible settings evolution.

> This is an evolving engineering project, not a claim of consciousness or frontier-level intelligence. The n-gram model is a lightweight fallback; LiteRT-LM requires a compatible pre-converted `.litertlm` model.

## Project documentation

- [A-to-Z architecture and implementation audit](docs/PROJECT_A_TO_Z.md)
- [Complete Android Debian installation and LiteRT-LM setup](docs/INSTALLATION_ANDROID_DEBIAN.md)
- [Project management workspace, API, security and roadmap](docs/PROJECT_MANAGEMENT.md)
- [GitHub updates, safe updater workflow and troubleshooting](docs/GITHUB_UPDATES_AND_PROJECTS.md)
- [Runtime settings, persistent logs, export and retention](docs/SETTINGS_AND_LOGGING.md)

## Quick start (Debian/Linux on Android)

```bash
git clone https://github.com/abdulraheemnohri/LIVING-AI.git
cd LIVING-AI
bash scripts/install_android_debian.sh
source .venv/bin/activate
bash scripts/run.sh
```

Open http://127.0.0.1:8000 in a browser. The server binds to localhost by default.

## Start automatically with your Linux session

After the app runs successfully once, configure startup:

```bash
bash scripts/enable_autostart.sh
```

On Linux environments with a working systemd user manager, this installs a user service. On Android Debian containers without systemd, it creates a helper and explains how to connect it to the terminal app's startup feature. Device-boot startup depends on host-app support and cannot be guaranteed from inside every Android container. See [Automatic startup guide](docs/AUTOSTART.md). Disable with `bash scripts/disable_autostart.sh`.

## Automatic model download and startup

The installer now installs the LiteRT-LM Python API and CLI and, by default, attempts to download the configured LiteRT-LM model during setup:

```bash
bash scripts/download_litert_model.sh
```

The automatic first-install download is controlled by `LIVING_AI_AUTO_DOWNLOAD_MODEL=true` in `.env.example`. It may use several GB of storage and mobile data and requires approximately 5.5 GB of free disk space. If download fails, installation continues and you can retry the command above. Existing model files are never overwritten. To skip the automatic download, set `LIVING_AI_AUTO_DOWNLOAD_MODEL=false` in `.env` before running the installer.

To enable systemd user-session autostart:

```bash
bash scripts/enable_autostart.sh
```

The managed startup service uses `scripts/start_managed.sh`. Automatic GitHub updates are **disabled by default**. Automatic model download is enabled for a fresh installation; you can opt out. Edit your private `.env`:

```dotenv
LIVING_AI_AUTO_UPDATE=true
LIVING_AI_AUTO_DOWNLOAD_MODEL=false
```

Only enable model auto-download if you accept the data/storage cost. Auto-update still requires a clean `main` checkout and passes the project checks. Android Debian containers without a systemd user manager need host-terminal startup support; a Linux helper script alone cannot register an Android boot receiver. See [Autostart guide](docs/AUTOSTART.md).

## Update an existing installation

From the repository directory, run:

```bash
bash scripts/update_android_debian.sh
```

The updater requires a clean Git working tree on `main` and a `.venv` created by the installer. It fetches `origin/main`, performs a fast-forward-only update, backs up `.env` and `data/` under a timestamped `backups/update-*` directory, reinstalls development dependencies, compiles Python modules, syntax-checks the dashboard when Node.js is available, and runs the test suite. If an update/check fails, it attempts to reset the code to the previous commit. Dependency changes may remain after rollback; inspect the error before restarting. Keep a separate backup of important data too.

## Hybrid architecture: Model B is the trainable model; Model A is the fallback

- **Model A — Character n-gram:** fallback/inference baseline only in the intended two-model workflow. It is not the target of the Model B training pipeline.
- **Model B — LiteRT-LM-compatible language model:** Model B is the model intended to be trained or fine-tuned. Important: LiteRT-LM is an inference runtime, not a training framework. Train/fine-tune the source model with a compatible external training stack, evaluate it, then convert/export it to a supported `.litertlm` artifact for local inference.
- **Hybrid mode:** tries the converted Model B through LiteRT-LM first, then falls back to saved local memory or Model A if Model B is unavailable or fails.

**Implementation status:** the repository has LiteRT-LM inference integration and existing local training code, but does not yet contain a Model B training/fine-tuning-and-conversion pipeline. The end-to-end runtime API, model generation and tests must be validated in the target environment; see [the A-to-Z audit](docs/PROJECT_A_TO_Z.md). The current Training Lab trains the character n-gram baseline, and the optional tiny Transformer trainer is a separate existing feature; these have not yet been replaced with Model B training. Imported SQLite memory is not automatically training data.

## Model B: Gemma 4 E2B Instruct (LiteRT-LM)

Use the published `litert-community/gemma-4-E2B-it-litert-lm` model as Model B. Its model file is `gemma-4-E2B-it.litertlm`, already packaged for LiteRT-LM inference; the repository's adapter expects it at `models/litert/gemma-4-E2B-it.litertlm`.

Install the official runtime package and prepare the model directory:

```bash
python -m pip install -e '.[litert]'
mkdir -p models/litert
```

Download the model file from the [Hugging Face model repository](https://huggingface.co/litert-community/gemma-4-E2B-it-litert-lm) into that directory, or try the official CLI directly:

```bash
pip install -U litert-lm
litert-lm run --from-huggingface-repo=litert-community/gemma-4-E2B-it-litert-lm gemma-4-E2B-it.litertlm --prompt="Hello"
```

The CLI command tests Model B independently; the LIVING AI app uses the local path configured in `.env`. Set `LIVING_AI_LITERTLM_MODEL_PATH` if you save it elsewhere. The model file is about 2.6 GB, and the model card reports roughly 1.7 GB CPU memory on a tested Android flagship; a 6 GB phone may still face memory pressure depending on Android/Linux overhead. Start with CPU mode. GPU requires compatible runtime and hardware.

Set these values in your `.env` file:

```dotenv
LIVING_AI_MODEL_BACKEND=hybrid
LIVING_AI_LITERTLM_MODEL_PATH=models/litert/gemma-4-E2B-it.litertlm
LIVING_AI_LITERTLM_BACKEND=cpu
LIVING_AI_MODEL_PATH=models/char_ngram.json
```

Supported `LIVING_AI_MODEL_BACKEND` values are `hybrid`, `litert_lm`, `char_ngram`, and the existing `tiny_transformer` backend aliases. In strict `litert_lm` mode, a load/generation error is reported. In `hybrid` mode, the app records a fallback response and reason in the chat API result. The installer automatically attempts the model download by default; it can be disabled with `LIVING_AI_AUTO_DOWNLOAD_MODEL=false`. If the download cannot complete, use the manual command above.

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
- Model A character n-gram fallback; Model B LiteRT-LM inference adapter (Model B training pipeline still pending)
- Mobile file import for TXT, Markdown and JSON plus explicit public webpage import
- Optional OpenAI-compatible chat-completions provider (opt-in)
- Allowlisted settings evolution with evaluation, snapshots, audit trail, and rollback
- Local installation scripts and unit tests

## Current training commands (legacy; not yet the Model B pipeline)

The existing command below trains the character n-gram baseline. It is not a Model B trainer. Do not treat it as the requested Model B training workflow:

```bash
python -m living_ai.train --input data/corpus --output models/char_ngram.json
```

This command only trains the existing character n-gram baseline. The Model B training/fine-tuning, evaluation, and conversion pipeline remains to be implemented.

## Optional remote provider

Set `LIVING_AI_ALLOW_REMOTE_PROVIDER=true`, `LIVING_AI_PROVIDER_URL`, `LIVING_AI_PROVIDER_MODEL`, and optionally `LIVING_AI_PROVIDER_API_KEY`. When enabled, chat text is sent to that configured endpoint. Keep secrets out of source control.

## Safety and evolution

The evolution engine can only change the explicitly allowlisted settings `temperature`, `max_reply_chars`, and `retrieval_limit`. Changes are validated, snapshotted, and audited. It does not execute arbitrary shell commands, install packages, or rewrite its own Python source. Automatic promotion is opt-in through `LIVING_AI_AUTO_PROMOTE=true`.

Before exposing the server on a network, set `LIVING_AI_ADMIN_PASSWORD` and review [SECURITY.md](SECURITY.md). Data lives under `LIVING_AI_DATA_DIR` (default `./data`).

## Development

```bash
python -m pip install -e '.[dev]'
python -m pytest
```

See `docs/ARCHITECTURE.md`, `docs/ANDROID_DEBIAN.md`, and the full [A-to-Z project audit and release checklist](docs/PROJECT_A_TO_Z.md).

## Current limitations

- The tiny from-scratch model is educational, not assistant-grade; training may be slow and PyTorch wheel support depends on architecture.
- LiteRT-LM uses the external Gemma 4 E2B Instruct `.litertlm` model and installed runtime; the model is about 2.6 GB on disk and memory needs may exceed what a phone can spare.
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


## Persistent AI Planner dashboard (review-first)

See [docs/EVOLUTION_LOOP.md](docs/EVOLUTION_LOOP.md). Tests are in
`tests/test_coordinator.py`.


## Persistent AI Planner dashboard (Phase 9)

The **AI Planner** view exposes the review-first evolution coordinator. Prepare a bounded plan with relevant past evaluations, inspect and persist it, submit it once to the registered-action queue, and record explicit human/caller outcome feedback. Planner endpoints require `LIVING_AI_ADMIN_PASSWORD`. Remote planning requires both request-level opt-in and `LIVING_AI_ALLOW_REMOTE_PROVIDER=true`; if enabled, the goal is sent to the configured remote provider. Preparing or submitting a plan never runs an execution cycle. See [docs/PLANNER_API.md](docs/PLANNER_API.md).


## Controlled Evolution Worker (Phase 10)

The Worker Control dashboard provides persistent enable/disable and pause/resume state, bounded manual ticks, per-goal approvals, recent execution history, and deterministic recommendations from explicitly reviewed outcomes. There is no background worker or automatic execution loop. Newly submitted planner steps are held in `needs_approval` until individually approved. See [docs/CONTROLLED_WORKER.md](docs/CONTROLLED_WORKER.md).


## Offline Evaluation Lab (Phase 11)

The **Evaluation Lab** runs eight fixed regression cases against the deterministic planner and persists run history in SQLite. It checks bounded step counts, preserved goals, explicit review requirements, action allowlisting, payload limits, and Unicode input handling. Open the Evaluation Lab dashboard page or use `POST /api/evaluation/run`; inspect history with `GET /api/evaluation/runs`. Both endpoints require `LIVING_AI_ADMIN_PASSWORD`.

This is a structural regression suite, not a semantic-quality benchmark. It does not invoke remote models, train weights, approve plans, or execute actions. See [docs/EVALUATION_LAB.md](docs/EVALUATION_LAB.md).


## Adaptive Learning & Regression Gate (Phase 12)

The Evaluation Lab now includes a persistent promotion gate. By default it requires three recent clean offline regression runs with 100% structural checks and blocks if history is insufficient, a run falls below threshold, result data is invalid, or the latest score regresses against the prior baseline. API: `POST /api/evaluation/gate/check?window=3&min_score=1.0`; history: `GET /api/evaluation/gate/history?limit=10`.

A pass means eligible for human review only. It does not promote/deploy code, change model weights, approve goals, or enable execution. See [docs/PROMOTION_GATE.md](docs/PROMOTION_GATE.md).


## Curated Learning Dataset Lab (Phase 13)

Use the admin-protected Dataset Lab API to stage examples as **pending**, review them explicitly, and export only approved examples to `data/corpus/curated_training.jsonl`. It deduplicates identical input/output pairs, preserves Urdu/Unicode, bounds payload sizes, and never starts training automatically. See [docs/CURATED_DATASET_LAB.md](docs/CURATED_DATASET_LAB.md). The current from-scratch trainer consumes text files, so the JSONL export must be deliberately converted/adapted before training.


## Runtime settings and persistent logs

The Settings page includes SQLite-backed runtime controls (temperature, reply length, memory retrieval limit), model/runtime configuration visibility, and an authenticated persistent log viewer with level filtering, export, and clear controls. Logs rotate locally beneath `LIVING_AI_DATA_DIR/logs/`; chat contents, credentials, API keys, and imported document contents are not written to operational logs. This is an operational log, not an immutable transcript or a compliance archive. See [docs/RUNTIME_SETTINGS_AND_LOGGING.md](docs/RUNTIME_SETTINGS_AND_LOGGING.md).

## Complete project reference

For the end-to-end architecture, UI inventory, model boundaries, settings, security, logging, backup/update operations, Android Debian setup, and release-readiness checklist, see [docs/COMPLETE_PROJECT_REFERENCE.md](docs/COMPLETE_PROJECT_REFERENCE.md). This guide explicitly distinguishes intended capabilities from features that still need runtime verification.

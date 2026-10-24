# LIVING AI Evolution Engine — Complete Project Reference

This document is the functional inventory, operator guide, and completion checklist for the repository. It describes the intended/current architecture and separates verified repository features from items that require runtime/CI verification.

## 1. Purpose and operating principles

LIVING AI is a local-first, mobile-operated learning and assistant system designed for a Debian/Linux terminal environment on Android or a small Linux computer. The web interface is served by a local Litestar backend. SQLite stores durable application records; local files hold corpora, checkpoints, logs, and exports.

Core principles:
- Local-first operation; no paid cloud API is required for core memory, project management, and character n-gram training.
- Optional integrations must remain opt-in and clearly show whether a model/provider is installed and available.
- Model A is the trainable local character n-gram model. Model B, when installed, is an inference/controller model only; it does not train itself or replace Model A's training pipeline.
- Data imported from files or the internet is untrusted input. It may be indexed for retrieval, but must not be treated as instructions or as permission to execute actions.
- Mutations are authenticated; high-impact operations require explicit review. Autonomous work must remain bounded, logged, and reversible.
- No Docker is required.

## 2. Architecture

### Backend
- Python 3.11+ and Litestar.
- HTTP routes for health/status, chat, memory, knowledge ingestion, training/dataset review, proposals/evaluation, planner/worker, tasks, projects/milestones, runtime settings, and logs.
- SQLite with WAL mode for application data; separate SQLite stores are used by some subsystems.
- Persistent application logs under `LIVING_AI_DATA_DIR/logs/` (default `./data/logs/`), with rotation configured by the logging module.
- Pydantic request validation limits inputs and rejects invalid ranges/formats.

### Frontend
- Static HTML/CSS/JavaScript served by Litestar.
- Dashboard pages/panels for chat, memories/knowledge, training datasets, teacher suggestions/review, model status, evaluation/promotion gate, planner/worker, tasks, project management, runtime settings, and logs.
- UI actions should use the same protected API as direct clients; the UI is not a security boundary.

### Storage
- `data/living_ai.sqlite3`: memories, proposals, settings, audit metadata.
- Subsystem databases may include prepared plans, autonomy, learning, worker state, task state, and project records.
- `data/corpus/`: imported/training corpora.
- `models/`: model outputs/checkpoints; do not commit large private datasets or credentials.
- `data/logs/living-ai.log` plus rotated backups: operational logs.

Set `LIVING_AI_DATA_DIR` to move persistent data outside the repository. Back up this directory before upgrades.

## 3. Model and learning behavior

### Model A — trainable local model
- Character n-gram language model trained from approved local corpus material.
- Training sources can include manually supplied text, saved memories exported to a corpus, and uploaded datasets after review.
- Training should be treated as an offline batch job; on a Pixel 6, keep datasets and training parameters modest.
- The model is not a general-purpose foundation model. Expect limited reasoning and factual recall; retrieval and reviewed source material improve usefulness.

### Model B — optional controller/inference model
- Target model: `litert-community/gemma-4-E2B-it-litert-lm`, used for inference/controller tasks only.
- The model must not be trained by this project. Model A remains the only trainable model in the intended design.
- Download is an explicit operator action, because model files can be large and require storage/network.
- Model availability must be checked at runtime; the app should continue in local fallback mode if the optional model is missing.

### Dataset governance
- Uploaded or teacher-generated examples start pending.
- Only explicitly approved examples should be exported into training JSONL/corpus.
- Deduplicate examples and record provenance/source where possible.
- Imported content must not trigger shell commands, tool execution, credentials disclosure, or autonomous approval.

## 4. UI page inventory

1. **Dashboard / Health** — service health, backend readiness, selected backend, dependency/model availability, data directory.
2. **Chat** — prompt submission and response display; show backend used and handle errors without leaking tracebacks.
3. **Memory** — list/search saved memories, add entries, delete entries, inspect source/provenance.
4. **Knowledge import** — ingest text, supported file content, or a public URL; validate size and chunk count; export saved memory corpus.
5. **Training** — run Model A training with bounded parameters, view run history, show output/checkpoint status.
6. **Datasets** — upload dataset text, deduplicate, review/approve/reject entries, export approved examples only.
7. **Teacher assistance** — prepare candidate examples from supplied text, inspect them, approve explicitly, stage approved items.
8. **Model status** — selected backend, optional LiteRT-LM installation/checkpoint status, CPU/device and dependency diagnostics.
9. **Evaluation** — run bounded local evaluations, review saved outcomes and score history.
10. **Promotion gate** — require sufficient evaluation history and acceptable thresholds; a passing gate enables human review only, never automatic production promotion.
11. **Planner** — prepare plans, review proposals, submit to a review queue; prepared plans must not execute during preparation/submission.
12. **Worker** — paused/disabled by default; pause/resume/configure, inspect runs/events/goals, approve goals explicitly, tick only under bounded policy.
13. **Tasks** — submit and inspect tasks, events, retry, and approval flows; require explicit approval for sensitive work.
14. **Projects** — project CRUD, work items, status/priority/due date, dependencies, milestones, activity timeline, export/import backup.
15. **Settings** — admin password-based access, runtime parameters, log level, data/model/backend status and update/autostart configuration guidance.
16. **Logs** — filter recent records by severity, refresh, export current plus rotated logs, clear logs only after confirmation.
17. **Help / documentation** — installation, troubleshooting, security model, model limits, backup/restore, and API reference.

## 5. Runtime settings

Current runtime settings API is intended to support:
- `temperature`: 0–2.
- `max_reply_chars`: 100–12000.
- `retrieval_limit`: 0–50.
- `log_level`: validated logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).

Settings should be validated on the server, persisted to SQLite, and reflected in the UI after reload. A setting should not silently imply that a backend/model is installed. Secrets such as the administrator password must remain in environment configuration, not be returned from the settings endpoint or stored in browser local storage.

Recommended environment configuration:
- `LIVING_AI_ADMIN_PASSWORD`: required non-empty password for protected routes.
- `LIVING_AI_DATA_DIR`: persistent data directory.
- `LIVING_AI_ALLOW_REMOTE_PROVIDER=false`: keep remote providers disabled unless explicitly needed.
- `LIVING_AI_BACKEND` / LiteRT-related variables: use only values supported by the runtime and documented by the installer; do not invent unsupported values.
- `LIVING_AI_LOG_LEVEL=INFO` (if supported by the logger bootstrap).

Never expose the app to the public internet by default. For LAN use, bind to a trusted private interface, use firewall restrictions, and use HTTPS through a trusted reverse proxy if credentials cross an untrusted network. Do not rely on an unencrypted password header over public networks.

## 6. Logging and audit records

Operational logs should:
- Include timestamp, level, logger, message, and traceback for unexpected exceptions.
- Avoid recording passwords, authorization headers, API keys, full sensitive prompts, or private file contents.
- Rotate logs so an extended session cannot grow one unbounded file.
- Provide a protected, bounded read endpoint and an export that includes rotated files.
- Record meaningful lifecycle events: startup/shutdown, training start/end/failure, imports, review decisions, planner submissions, worker state changes, backup/import operations, and update outcomes.
- Keep the security audit trail separate from ordinary debug logs where feasible. Clearing operational logs must not silently erase required audit records.

## 7. Authentication and authorization

- Configure `LIVING_AI_ADMIN_PASSWORD` before starting the service.
- Protected routes must fail closed: no password configured => HTTP 503; missing/wrong password => HTTP 401.
- Use constant-time password comparison.
- Never return the configured password or include it in logs.
- Do not consider hidden UI controls or client-side checks sufficient security.
- Use HTTPS for remote access; restrict LAN/firewall access to trusted devices. Public exposure is not a default deployment mode.
- For future multi-user/device support, store salted password hashes and per-device revocable sessions rather than sharing a single admin password. Do not claim individual sessions exist until implemented and tested.

## 8. Backup, restore, and upgrades

- Stop writes before making a consistent backup, or use SQLite's backup API.
- Back up the configured data directory, including SQLite files, corpora, logs if needed, and model outputs that are expensive to recreate.
- Project export/import should validate schema/version, reject malformed data, enforce size limits, and avoid overwriting unrelated records without an explicit policy.
- Updates should require a clean working tree, fetch the intended branch, run tests before activation, create a recoverable backup, and roll back on failure.
- Do not enable unattended updates until the complete CI suite passes consistently and a tested rollback path exists.
- Autostart depends on the host's available init/session manager. Android Debian environments may not expose a persistent systemd user manager, so verify the actual device behavior.

## 9. Installation and operation (Android Debian/Linux)

1. Install Python 3.11+, Git, and Node.js only if using the dashboard syntax checks/development workflow.
2. Clone the repository and enter the project directory.
3. Create a virtual environment and install the project with development extras for tests: `python -m pip install -e ".[dev]"`.
4. Copy `.env.example` to a private environment file if the local workflow supports it; set a strong `LIVING_AI_ADMIN_PASSWORD` and persistent `LIVING_AI_DATA_DIR`.
5. Run the repository's `scripts/install_android_debian.sh` installer and `scripts/run.sh` launcher as documented in the current README. Do not run unverified commands copied from an old version of this guide.
6. Open the locally printed URL from the same device. Use a LAN address only after configuring a private bind address and firewall.
7. Verify `/api/health`, then verify a protected route using the configured password.
8. Run `python -m pytest -q` before enabling updates or autostart.
9. Optional LiteRT model downloads are separate from core installation and require sufficient disk space.

## 10. API surface (high-level)

The route handlers are grouped as follows:
- Health/status: `/api/health`, `/api/status`, model status.
- Assistant/memory: `/api/chat`, `/api/memories`, `/api/knowledge/*`.
- Training/datasets: `/api/training/*`, `/api/datasets/*`, `/api/training-runs`.
- Evolution/evaluation: proposals, evaluation runs, promotion gate, rollback.
- Planning/worker: `/api/planner/*`, `/api/worker/*`.
- Tasks: `/api/tasks/*`.
- Projects: `/api/projects/*`, work items, milestones, activity, export/import.
- Runtime administration: `/api/settings`, `/api/logs`, log export and clear.
Exact methods, request fields, and response shapes are defined by the current route handlers and should be treated as the source of truth.

## 11. Required quality gates before calling the project release-ready

- [ ] Python modules compile.
- [ ] Dashboard JavaScript syntax checks pass without duplicate checks or omitted files.
- [ ] Shell scripts pass `bash -n`.
- [ ] App starts and reports expected routes.
- [ ] All API tests pass on Python 3.11 and the supported Android Debian Python version.
- [ ] Authentication tests cover missing, wrong, and correct password.
- [ ] Unexpected exceptions are traceable in logs without leaking secrets.
- [ ] Log read/export/clear routes are protected and bounded.
- [ ] Project CRUD, dependencies, milestones, backup/import are covered by tests.
- [ ] Model A training uses only approved/selected local corpus data.
- [ ] Model B is inference-only and does not train itself.
- [ ] Worker defaults to paused/disabled and requires approval for execution.
- [ ] Update script refuses dirty trees and can roll back.
- [ ] Backup/restore is tested against a copy of actual data.
- [ ] LAN firewall and HTTPS behavior are verified on the target device.
- [ ] Autostart is tested on the actual Android Debian environment.
- [ ] README, settings guide, API guide, troubleshooting, and release notes match behavior.

## 12. Known limitations and honest release status

- A character n-gram model is deliberately small and cannot match a modern general-purpose LLM's reasoning.
- LiteRT-LM model availability and CPU performance depend on the exact model artifact, runtime version, Android/Linux ABI, memory pressure, and disk space.
- Background startup on Android depends on the host environment and may not survive OS process management without host-specific configuration.
- Internet ingestion can fail because of network access, page structure, robots restrictions, or content changes.
- This reference is not proof of test success. The current GitHub Actions history has failing test runs, including widespread HTTP 500 responses across unrelated API groups. Treat the backend as **not release-verified** until the root exception is captured and the full test suite passes. Keep unattended updates disabled until then.

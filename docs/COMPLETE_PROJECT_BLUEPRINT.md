# LIVING AI Evolution Engine — Complete Project Blueprint

## 1. Purpose and operating principles

LIVING AI is a local-first, self-improving assistant designed to run on a Debian/Linux userspace on Android (including a Pixel 6) or on ordinary Linux. The system must remain useful without paid cloud APIs. Internet access is optional and must be explicitly enabled for features that need it.

Core principles:
- Local data and models by default; no telemetry by default.
- Clear separation between inference, trainable learning, planning, and execution.
- Human approval for consequential actions, model promotion, destructive changes, and external side effects.
- Every autonomous action is policy-checked, bounded, recorded, and reversible where practical.
- Never describe a proposed, queued, or simulated action as completed.
- Fail closed when administrator authorization is missing or invalid.
- No Docker requirement.

## 2. Model strategy

### Model A — trainable local learner
- Character n-gram model is the low-resource baseline and the only model that this project trains by default.
- Training inputs may come from user-supplied TXT, Markdown, JSON/JSONL, approved local memories, or reviewed datasets.
- Keep source metadata, dataset hashes, training parameters, timestamps, and output checksums.
- Use validation samples and compare against the previous model before promotion.
- Save checkpoints and preserve a rollback copy.
- Never automatically train on arbitrary fetched web pages without review.

### Model B — optional assistant/controller
- Optional LiteRT-LM model: `litert-community/gemma-4-E2B-it-litert-lm`.
- Inference/controller only; do not train Model B.
- Model B may help explain data, propose training examples, summarize evaluation results, or draft a plan, but outputs are untrusted suggestions.
- Model B must not bypass authorization, policy checks, evaluation gates, or human approval.
- The application must remain usable when Model B is unavailable. Show clear download, storage, and runtime status.
- Do not silently switch to paid providers or remote inference.

## 3. Main architecture

- **Litestar backend:** HTTP API, request validation, authorization, lifecycle.
- **Static web dashboard:** HTML/CSS/JavaScript, usable from the phone browser.
- **SQLite:** settings, memories, dataset records, proposals, project/work-item data, milestones, activity, tasks, evaluation history, worker state, audit events.
- **Model/data directories:** versioned local artifacts and corpus files.
- **Logging subsystem:** rotating application logs plus structured audit events.
- **CLI scripts:** install, run, health check, model download, backup, update, and optional boot startup.
- **GitHub Actions:** Python tests, JavaScript syntax checks, and workflow validation.

Keep routes thin. Business logic belongs in focused modules; all filesystem paths must be validated and confined to configured data/model roots.

## 4. Dashboard pages and expected functions

### Dashboard / Overview
- Backend health, uptime, version, selected backend, model readiness, memory count, dataset count, queued plans, pending approvals, latest training/evaluation, disk usage.
- Refresh and error states must be visible. A health indicator must reflect a real health endpoint, not a hard-coded green status.

### Chat
- Local response generation, bounded output, source/context display where available, clear model/backend status.
- Show errors honestly when no model is available.
- Optional memory retrieval controlled by runtime settings.
- Never imply that generated content is verified fact.

### Memory and Knowledge
- Search, add, inspect, delete, and export memories.
- Import TXT/Markdown/JSON and bounded URL ingestion when internet ingestion is enabled.
- File type, size, chunk count, and URL/network restrictions enforced server-side.
- Preview sources and remove incorrect or unwanted entries.
- Corpus export includes provenance and warns users to review licensing and quality.

### Training Lab / Dataset Lab
- Upload and list datasets; deduplicate examples; review pending examples; approve/reject explicitly.
- Prepare teacher-suggested examples as pending only.
- Export approved records to UTF-8 JSONL.
- Show training history, dataset hashes, parameters, duration, output path, evaluation metrics, and failures.
- Training should run in a worker thread/process with cancellation and progress reporting, not block normal API requests.
- Only Model A is trainable by default.

### Evaluation and Promotion Gate
- Run bounded offline evaluation against a fixed validation set.
- Record baseline and candidate metrics with timestamp and model hash.
- Reject empty/insufficient evaluation windows and metric regressions.
- A passing gate means “eligible for human review,” not automatic permission to promote.
- Promotion creates a backup and records an audit event. Rollback restores the last known-good artifact.

### Planner
- Turn a user goal into a visible plan with discrete steps, risk, dependencies, expected outputs, and estimated resource needs.
- Prepare and save a plan without executing it.
- Allow editing, canceling, approval, submission, and recording evaluation.
- Reject duplicate submissions and invalid state transitions.

### Autonomous Worker
- Starts paused and stays paused after installation/restart unless the administrator explicitly enables it.
- Modes: disabled, paused, approval-required, and bounded pre-approved reversible actions.
- Configurable maximum steps per tick, time budget, retries, network access, and allowed action categories.
- Require approval for external messages, destructive filesystem changes, credential changes, publishing, purchases, privilege escalation, and model promotion.
- Idempotency keys, action timeouts, audit records, and cancellation.
- Circuit breaker pauses the worker after repeated failures.

### Projects and Tasks
- Projects, work items, statuses, priorities, due dates, dependencies, milestones, activity timeline.
- Validate status transitions and dependency relationships.
- Prevent circular dependencies; clean references when a prerequisite is deleted.
- JSON backup/export/import with schema version, validation, size limits, and safe merge/replace behavior.
- Import preview before applying changes.

### Evolution / Proposals
- Store proposed changes with rationale, scope, risk, test plan, evaluation, approval state, and rollback plan.
- Do not self-edit running code or execute arbitrary model-generated shell commands.
- Use reviewed patch files or Git branches; run tests before merge.
- Never commit secrets, data, model weights, or logs to the repository.

### Settings
- Runtime: temperature, reply character limit, retrieval count, model backend, data directory, host, port.
- Logging: DEBUG/INFO/WARNING/ERROR/CRITICAL, log viewer, filters, export, rotate, clear with confirmation.
- Security: administrator password configured through environment; never display or log the password.
- Models: selected backend, model path, download status, available storage, device/runtime status.
- Autonomy: worker enable/pause, approval policy, action limits, network access, retry limits.
- Updates: check-only by default, update channel, last checked commit, backup and rollback policy.
- Startup: status of supported startup mechanism and clear warning if host systemd/user services are unavailable.
- Backups: create, list, verify, export, and restore after explicit confirmation.
- Settings must be validated server-side; frontend constraints alone are not security.

### Logs and Audit
- Rotating logs stored under the configured data directory, not tracked in Git.
- Include timestamps, severity, logger, request correlation ID, operation result, and exception tracebacks.
- Do not log passwords, authorization headers, full sensitive content, or secrets.
- Log viewer supports level filter, bounded pagination, export of current and rotated files.
- Audit log records security-sensitive changes, approvals, model promotion/rollback, imports, worker state changes, and update actions.
- Log clearing requires admin authorization and confirmation; retain separate audit events for log-clear operations where possible.
- Unexpected exceptions return a generic error to clients while the server log preserves diagnostic detail.

## 5. Authorization and security

- Use `LIVING_AI_ADMIN_PASSWORD` from the environment. Do not hard-code credentials.
- Protected routes must reject missing configuration (503) and invalid credentials (401).
- Use constant-time password comparison where applicable.
- Bind to `127.0.0.1` by default. Binding to a LAN/public interface requires an explicit configuration and a warning.
- Restrict CORS; enforce request size limits and strict input validation.
- URL ingestion must block loopback, private, link-local, reserved, and metadata-service addresses after DNS resolution and on redirects; use timeouts and response-size limits to reduce SSRF risk.
- Confine paths to allowed directories; reject traversal and symlink escapes.
- Never run arbitrary shell commands supplied by a model, web page, dataset, or user prompt.
- Treat fetched documents and model output as untrusted input.
- Redact secrets in logs and error responses.

## 6. Runtime configuration

Recommended environment variables:
- `LIVING_AI_HOST=127.0.0.1`
- `LIVING_AI_PORT=8000`
- `LIVING_AI_DATA_DIR=./data` (choose persistent writable storage on Android)
- `LIVING_AI_ADMIN_PASSWORD` (required for admin routes)
- `LIVING_AI_MODEL_BACKEND=char_ngram`
- `LIVING_AI_LOG_LEVEL=INFO`
- `LIVING_AI_AUTO_UPDATE=false`
- `LIVING_AI_AUTO_DOWNLOAD_MODEL=false`
- `LIVING_AI_AUTO_PROMOTE=false`

Keep secrets in an untracked `.env` file or shell environment; commit only `.env.example`. Validate configuration on startup and show actionable messages for invalid values.

## 7. Install, run, update, backup, and startup

- Install through the repository's Debian/Linux installation script and a Python virtual environment.
- Run through the managed start script; expose the web UI only on the configured host/port.
- Add a health-check command that verifies the server, database, writable data directory, model readiness, and frontend assets.
- Backups must include SQLite data and configuration metadata; model artifacts may be included only when requested due to size.
- Restore must verify backup integrity and preserve a pre-restore copy.
- GitHub updates must be opt-in/check-only by default, require a clean work tree, fetch and fast-forward only, create a backup, run tests, and roll back on failure.
- Do not run `git reset --hard` against user changes.
- Auto-start is host-dependent: use a user service only when the Android Debian environment actually supports a persistent systemd user manager; otherwise document a supported host-specific launcher. Do not claim guaranteed boot startup without testing on the device.

## 8. API contract

- Health endpoint is public and returns only non-sensitive readiness information.
- Administrative data and mutation endpoints require admin authorization.
- Use consistent JSON errors: status code, safe detail, and optional correlation ID.
- Use 400 for invalid input, 401 for invalid credentials, 404 for missing records, 409 for conflicts, 413 for oversized requests, 503 when administrative operations are locked by missing configuration, and 500 for unexpected errors.
- Add tests for every route's success path, validation failures, authorization failures, persistence, and restart behavior.

## 9. Quality gates and test plan

Required CI checks:
1. Install dependencies on a clean runner.
2. Python compile/import check.
3. Full pytest suite with failure tracebacks preserved.
4. JavaScript syntax checks for every frontend script.
5. Duplicate HTML ID and JavaScript selector consistency check.
6. Shell syntax checks for install/update/start scripts.
7. Workflow YAML syntax check.
8. Verify no tracked secrets, runtime databases, logs, or large model weights.
9. Test clean install and update rollback in a disposable environment.
10. Test on the target Android Debian environment for storage, memory, ports, model inference, and startup persistence.

Release gate: all required CI checks must pass. Do not enable auto-updates or claim the release is complete while the test suite is failing.

## 10. Resource and operational limits

- Character n-gram training is the recommended low-memory default.
- A multi-billion-parameter LiteRT-LM model can require several GB of storage and substantial RAM; actual viability depends on quantization, runtime, device memory, and Android userspace compatibility.
- Never download a large model automatically unless explicitly enabled and enough free space is available.
- CPU-only inference may be slow. Report backend status and resource limitations honestly.
- Use bounded queues, bounded datasets, and bounded evaluation windows to protect the phone from memory exhaustion.

## 11. Release checklist

- [ ] Fresh Debian/Linux install succeeds.
- [ ] Admin auth passes missing/wrong/correct password tests.
- [ ] Health and dashboard accurately report readiness.
- [ ] Runtime settings persist after restart.
- [ ] Logs rotate, export, filter, and redact sensitive data.
- [ ] Project CRUD, dependencies, milestones, backup, and import pass tests.
- [ ] Dataset review/export and Model A training pass tests.
- [ ] Model B remains inference-only.
- [ ] Evaluation gate blocks regressions and requires human approval.
- [ ] Worker starts paused and cannot bypass approval policy.
- [ ] Update process backs up, tests, and rolls back safely.
- [ ] All CI checks pass.
- [ ] Device-specific startup behavior has been tested rather than assumed.

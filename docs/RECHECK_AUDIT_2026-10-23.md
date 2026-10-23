# LIVING-AI Repository Recheck — 2026-10-23

## Scope

Reviewed the recursive repository tree (87 tracked files), core Litestar route registration, admin-password guards, dashboard markup and script loading, task lifecycle code, installer/updater scripts, CI workflow, security notes, and A-to-Z project documentation. This is a source-level audit; it is not a substitute for running the app on the target Android Debian/Linux environment.

## Fixes applied during this recheck

1. Registered the existing task lifecycle endpoints from `living_ai/task_api.py` in `living_ai/app.py`. Before this fix, the task lifecycle API implementation existed but was not part of the Litestar application's route list.
2. Added a Task Queue dashboard navigation item and page with task submission, task history, bounded-cycle execution confirmation, and refresh controls.
3. Loaded `static/tasks.js` from the dashboard so the Task Queue page's controls are wired to the API.
4. Restored authentication regression cases for `POST /api/tasks`; the route now exists and is guarded by the admin-password check.
5. Added `static/tasks.js` to the dashboard JavaScript syntax checks.
6. Added shell syntax checks for the install, run, training, and update scripts in GitHub Actions.
7. Hardened the updater's fast-forward check to stop explicitly if the local branch cannot safely fast-forward.

## Current page inventory

- Overview / runtime status
- Chat
- Persistent memory and search
- Import Data (local files, public URL, corpus export)
- Training Lab (dataset upload, teacher candidates, n-gram training, optional tiny Transformer)
- Reversible Evolution proposals and rollback
- AI Planner and reviewed outcomes
- Controlled Worker and approval queue
- Task Queue and task/event inspection
- Offline Evaluation Lab
- Audit trail
- Settings (admin password for the current tab, model backend status)

## Current API/security design

- Admin endpoints require `X-Admin-Password` matching `LIVING_AI_ADMIN_PASSWORD`; missing configuration fails closed with HTTP 503, and incorrect passwords return HTTP 401.
- Password comparison uses `hmac.compare_digest`.
- Dashboard password is held in browser `sessionStorage` for the current tab session; clear it when finished.
- The default host should remain `127.0.0.1`. A password header alone is not transport encryption; use HTTPS and network controls before remote exposure.
- `/api/health` is intentionally public. `/api/chat` is currently also public; review whether that is desired before exposing the service to a network because chat can consume resources and may use an optional remote provider when configured.
- The task engine exposes only registered actions and the current built-in action is `save_note`; a task cycle must be triggered explicitly. Keep the worker paused/manual and do not introduce shell execution.

## Feature and implementation status

Implemented source modules cover local memory, lexical retrieval, n-gram training, optional tiny byte-level Transformer training, optional LiteRT-LM inference, knowledge ingestion, planner, bounded task lifecycle, worker, evaluation gate, curated examples, and reversible settings evolution.

Important limitations that must remain visible in UI/docs:
- LiteRT-LM is inference, not training. A tested Model B fine-tuning/export/conversion pipeline is not implemented.
- Model status checks dependencies/files; it does not prove the full model loads or generates successfully on the device.
- Imported memory is not automatically training data.
- Public webpage import uses best-effort SSRF checks and is not a hardened network sandbox.
- The tiny Transformer is educational and can be slow or memory-heavy on mobile.
- UI/model runtime should be smoke-tested on the target Android Debian/Linux distribution and actual device before claiming end-to-end readiness.

## Verification

GitHub Actions runs syntax checks for JavaScript and shell scripts, compiles Python modules, checks Litestar application startup, and runs pytest. See the latest workflow at:
https://github.com/abdulraheemnohri/LIVING-AI/actions

This audit does not claim the newest commit is green until its workflow run completes successfully.

# Persistent AI Planner API

Phase 9 connects the review-first coordinator to the dashboard and persists prepared plans so a plan can be inspected and submitted in a later request.

## Security and remote-provider behavior

Every `/api/planner/*` route fails closed unless `LIVING_AI_ADMIN_TOKEN` is set. Requests must include `Authorization: Bearer <token>`. Remote planning is enabled only when both the request sets `allow_remote: true` and the server environment sets `LIVING_AI_ALLOW_REMOTE_PROVIDER=true`; otherwise planning remains deterministic/local. If enabled, goal text may be sent to the configured remote provider.

## Endpoints

- `POST /api/planner/prepare` — JSON `{ "goal": "...", "allow_remote": false, "memory_limit": 5 }`. Returns a plan and similar prior evaluations, stores it locally, and does not queue or execute actions.
- `GET /api/planner/proposals?limit=30` — lists prepared/submitted plans and metadata.
- `POST /api/planner/submit` — JSON `{ "plan_id": "..." }`. Validates the stored plan and queues only the fixed `save_note` action. A plan can be submitted once; duplicate submission returns HTTP 409. No execution cycle is run.
- `POST /api/planner/evaluations` — records explicit caller/human feedback: goal, score from 0 to 1, outcome, optional feedback, summary and tags.
- `GET /api/planner/learning-summary` — returns aggregate evaluation counts and score summary.

## Storage

Prepared plans are stored in `prepared_plans.sqlite3` under `LIVING_AI_DATA_DIR`; evaluation history uses `learning.sqlite3`, and queued goals use `autonomy.sqlite3`. These remain local files. Back them up and restrict filesystem access.

## Dashboard

Open **AI Planner** to prepare a plan, inspect its structured output and prior evaluations, submit it for review, view plan history, and record a reviewed outcome. The UI clearly reports that preparation/submission do not execute actions. The API does not start a worker, timer, or automatic run loop.

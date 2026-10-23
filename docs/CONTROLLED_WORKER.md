# Controlled Evolution Worker (Phase 10)

The worker adds durable controls around the existing goal queue. It is intentionally **manual-only**: no background thread, timer, or daemon starts automatically. Worker state is persisted in `worker.sqlite3` under `LIVING_AI_DATA_DIR`.

## Safety model

1. Preparing a plan does not queue actions.
2. Submitting a plan queues its steps in `needs_approval`, not `queued`.
3. A reviewer must approve each individual goal.
4. The worker must be enabled and resumed before a manual tick can process queued goals.
5. Every tick processes at most the engine's bounded batch and increments the persistent cycle budget.
6. Pause/disable prevent further ticks. Reaching the cycle budget pauses the worker.
7. Only registered actions can run; the current planner API only accepts `save_note`.
8. Evaluation recommendations summarize explicitly recorded feedback. They do not grant permissions or modify code.

## API

All endpoints require `Authorization: Bearer <LIVING_AI_ADMIN_TOKEN>`; if the token is not configured, endpoints fail closed.

- `GET /api/worker/status` — controls, goal queue, recent runs, events, pending approvals.
- `POST /api/worker/enable`, `/disable`, `/resume`, `/pause` — change persistent control state. Resume does not start a daemon.
- `POST /api/worker/configure` — JSON `{"max_cycles_per_run": 3}`, allowed range 1–10; configuration pauses the worker.
- `POST /api/worker/tick` — run exactly one manual tick if enabled and resumed.
- `POST /api/worker/goals/{goal_id}/approve` — approve one held goal; it is queued but not immediately executed.
- `POST /api/worker/recommendations` — JSON `{"goal":"...","limit":5}`, retrieves similar reviewed outcomes and gives deterministic review suggestions.

## Suggested operator workflow

1. Prepare a goal in AI Planner and inspect the proposed steps.
2. Submit it for review.
3. Open Worker Control and inspect the held goals.
4. Approve each specific goal you intend to run.
5. Enable and resume the worker, then use **Run one manual tick**.
6. Inspect results and event history. Pause or disable when finished.
7. Record a human-reviewed outcome in AI Planner so later recommendations have evidence.

The worker never automatically approves tasks, starts background execution, runs arbitrary shell commands, or rewrites repository source files.

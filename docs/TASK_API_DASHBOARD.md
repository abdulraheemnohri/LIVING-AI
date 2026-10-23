# Task lifecycle API and dashboard

Phase 8 exposes the existing bounded task lifecycle to the local dashboard.

## Security

All `/api/tasks` routes require `LIVING_AI_ADMIN_TOKEN`. If it is unset, these endpoints fail closed with HTTP 503; a wrong or missing bearer token returns HTTP 401. Configure a strong token in the private environment file and restart the server. The dashboard uses the token already stored for the current browser tab in Settings. Do not expose this server publicly without TLS and a reviewed network access policy.

## Endpoints

- `GET /api/tasks?limit=50` — list recent tasks (limit clamped to 1–200).
- `POST /api/tasks` — submit a task with `title`, registered `action`, and JSON `payload`. This queues only; it does not execute.
- `GET /api/tasks/{task_id}` — task details and recent event history.
- `GET /api/tasks/{task_id}/events?limit=50` — event history.
- `POST /api/tasks/run-once` — explicitly run one bounded engine cycle.
- `POST /api/tasks/{task_id}/retry` — explicitly retry a failed task within its configured retry budget.
- `POST /api/tasks/{task_id}/approve` — release a task held for approval back to the queue.

The first dashboard action is `save_note`, which saves a local note. Unknown actions cannot be submitted through the lifecycle wrapper. The engine remains the final execution-policy gate; approval does not make an unregistered action executable. The API does not start a daemon or background worker.

## Dashboard

Open **Tasks** to queue a note, inspect status and event history, approve a held task, retry a failed task, or manually run one cycle. The cycle button asks for confirmation because registered reversible actions may execute immediately.

## Storage

The engine queue is stored in `data/autonomy.sqlite3` (or under `LIVING_AI_DATA_DIR`), and lifecycle records/events are stored in `task_lifecycle.sqlite3` in the same data directory. These are separate SQLite databases; keep the data directory private and back it up deliberately.

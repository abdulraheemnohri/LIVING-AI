# Task lifecycle (Phase 7)

`living_ai.lifecycle.TaskLifecycle` adds a logical task record and event history around
`AutonomyEngine`. It is intentionally a library, not a background worker.

## Example

```python
from living_ai.autonomous import AutonomyEngine
from living_ai.lifecycle import TaskLifecycle

engine = AutonomyEngine("data/autonomy.sqlite3")
tasks = TaskLifecycle(engine, "data/task_lifecycle.sqlite3", max_retries=2)

task = tasks.submit("Save a project note", "save_note", {"text": "Review phase 7"})
print(task["task_id"], task["status"])

# Explicitly process one bounded cycle; no timer or daemon is started.
print(tasks.run_once())
print(tasks.events(task["task_id"]))

# Retry only after a recorded failure, and only within the configured budget.
# tasks.retry_failed(task["task_id"])
```

## Lifecycle and safeguards

- States reflect the engine outcome: `queued`, `completed`, `failed`, or `needs_approval`.
- Only actions already registered with the engine can be submitted.
- `run_once()` explicitly invokes one existing bounded engine cycle; it does not loop.
- Failed retries are explicit, capped at 0–5, and create a new engine goal.
- The engine still decides whether an action is reversible, enabled for auto-run, or needs approval.
- Task payloads and event details are stored in a local SQLite database.
- This module does not start threads, timers, a server, or any background service.

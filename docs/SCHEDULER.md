# Opt-in autonomy scheduler

`living_ai.scheduler.AutonomyScheduler` provides an explicit pause/resume gate, a minimum
interval between cycles, disable/enable controls, a per-run cycle budget, and a status snapshot.
It uses only the Python standard library and wraps the goal engine; it does not spawn a thread,
start a daemon, or run automatically at import time.

## Example

```python
from living_ai.autonomous import AutonomyEngine
from living_ai.scheduler import AutonomyScheduler

engine = AutonomyEngine("data/autonomy.sqlite3", auto_run_reversible=True)
scheduler = AutonomyScheduler(engine, interval_seconds=60, max_cycles_per_run=10)
scheduler.resume()                 # explicit opt-in
print(scheduler.tick())            # run only when due
print(scheduler.status())          # dashboard-ready status
scheduler.pause()                  # immediate pause before next cycle
```

A host service may call `tick()` on its own controlled loop. Always expose pause/disable status
to the user and avoid starting background work by default. The scheduler's cycle budget is
in-memory; persistent goal and action history remain in the engine's SQLite database.

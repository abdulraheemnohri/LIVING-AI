# Bounded autonomy engine

The optional `living_ai.autonomous.AutonomyEngine` provides a durable goal queue, bounded cycles,
a registered-action policy, reversible-action auto-run, approval holding, saved notes, and an audit log.
It uses the Python standard library.

## Safety guarantees
- Only explicitly registered actions can run.
- Unknown and non-reversible actions are held for approval.
- Automatic execution can be disabled with `auto_run_reversible=False`.
- Each attempted action is logged; exceptions are recorded as failed runs.
- Each cycle runs at most 3 actions by default (configurable, hard maximum 25).
- No shell commands, arbitrary code evaluation, package installation, or source-code self-rewrites.
- Approval does not bypass the registry: an unknown action remains blocked until implemented and registered.

## Example
```python
from living_ai.autonomous import AutonomyEngine
agent = AutonomyEngine("data/autonomy.sqlite3", auto_run_reversible=True)
agent.add_goal("Keep project idea", "save_note", {"text": "Explore an offline assistant"})
print(agent.cycle())
print(agent.list_goals())
print(agent.list_runs())
```

The built-in `save_note` is the reference action. This module does not start a background daemon
or silently alter the dashboard/API. A scheduler and UI integration should be added as separately
reviewable steps, with pause/resume controls and resource budgets.


## Scheduling

For explicit interval and pause/resume controls, see [SCHEDULER.md](SCHEDULER.md). The scheduler is
opt-in and does not start background work automatically.

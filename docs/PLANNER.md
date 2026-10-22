# Goal planner (Phase 3 foundation)

`living_ai.planner.GoalPlanner` turns a high-level goal into a bounded, inspectable proposal.
This first planner is intentionally deterministic: it splits text into at most 5 planning items and
proposes the built-in `save_note` action. Every step is marked for review.

## Example

```python
from living_ai.autonomous import AutonomyEngine
from living_ai.planner import GoalPlanner

engine = AutonomyEngine("data/autonomy.sqlite3", auto_run_reversible=False)
planner = GoalPlanner(engine, max_steps=5)
proposal = planner.plan("Prepare a project outline. Identify risks. Record next steps.")
print(planner.to_dict(proposal))      # inspect before queueing
queued_ids = planner.submit_for_review(proposal)
print(engine.list_goals())            # queued, not executed by the planner
```

## Boundaries

- No network access, LLM calls, shell execution, or source-code modification.
- Planning and execution are separate operations.
- Submitting queues tasks; it does not execute them in the planner.
- The engine's action registry and reversible-action policy remain the execution gate.
- This is a baseline decomposition scaffold, not a claim of advanced reasoning. Replace it with a
  model-backed planner only after adding prompt-injection defenses, schema validation, evaluations,
  explicit tool permissions, and a review UI.

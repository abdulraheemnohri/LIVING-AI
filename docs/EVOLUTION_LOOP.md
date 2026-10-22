# Evolution coordinator

Phase 6 connects the goal planner, optional cognitive adapter, local evaluation memory, and persistent autonomy queue.

## Basic use

```python
from living_ai.autonomous import AutonomyEngine
from living_ai.coordinator import EvolutionCoordinator
from living_ai.learning import LearningStore

engine = AutonomyEngine("data/autonomy.sqlite3")
learning = LearningStore("data/learning.sqlite3")
evolution = EvolutionCoordinator(engine, learning=learning)

prepared = evolution.prepare("Review the offline search feature")
print(prepared.to_dict())  # plan + similar past evaluations; no queue changes

goal_ids = evolution.submit_for_review(prepared)  # queue only; no execution
print(goal_ids)

# Record only an outcome that was actually reviewed/observed.
evolution.record_evaluation(
    "Review the offline search feature",
    score=0.8,
    outcome="Manual review completed",
    feedback="Keep all retrieval local",
)
print(evolution.learning_summary())
```

## Safety boundaries

- `prepare()` only creates a plan and retrieves similar stored evaluations.
- Prior evaluations are returned as inspectable context; v1 does not inject them into model prompts.
- Remote planning remains opt-in via `prepare(..., allow_remote=True)`.
- `submit_for_review()` only persists queued proposals. It does not call `engine.cycle()`.
- The autonomy engine's registered-action, reversibility, and auto-run settings remain authoritative.
- Scores/outcomes are supplied by the caller; the coordinator does not pretend to verify task success.
- SQLite data remains local to the configured paths; retrieval is lightweight lexical matching.

# Cognitive Core (Phase 4 foundation)

The `living_ai.cognitive.CognitiveCore` adds optional model-assisted goal decomposition over the
existing conservative planner. It does not add a mandatory dependency: the existing
OpenAI-compatible provider is already opt-in through environment configuration.

## Usage

```python
from living_ai.autonomous import AutonomyEngine
from living_ai.planner import GoalPlanner
from living_ai.cognitive import CognitiveCore

engine = AutonomyEngine("data/autonomy.sqlite3")
core = CognitiveCore(GoalPlanner(engine))
result = core.plan("Prepare a project plan and identify risks", allow_remote=False)
print(result.backend, core.planner.to_dict(result.plan))
# Inspect first, then queue for review:
goal_ids = core.submit_for_review(result)
```

Set `allow_remote=True` only when you explicitly want to try the configured compatible provider.
The provider remains disabled unless `LIVING_AI_ALLOW_REMOTE_PROVIDER=true` and its URL/model are
configured. Without that opt-in, the deterministic planner is used.

## Trust boundaries

- Model output is untrusted and parsed as a strict JSON schema.
- Model output controls only short text labels; it cannot select arbitrary action names.
- Every step is marked `requires_review=True`.
- Planning and queue submission do not execute actions.
- Invalid, unavailable, or malformed provider responses fall back to the deterministic planner.
- This is task decomposition, not proof of model quality; evaluate results before relying on them.

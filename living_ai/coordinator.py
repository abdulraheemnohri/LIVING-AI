"""Review-first coordinator joining planning, prior evaluations, and durable memory.

Preparation, submission, and evaluation are separate operations. This coordinator
never invokes AutonomyEngine.cycle() and never executes actions by itself.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .autonomous import AutonomyEngine
from .cognitive import CognitiveCore
from .learning import LearningStore
from .planner import GoalPlanner, Plan


@dataclass(frozen=True)
class PreparedEvolution:
    """A plan plus relevant past evaluations, ready for human inspection."""

    plan: Plan
    backend: str
    warning: str | None
    prior_evaluations: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan": GoalPlanner.to_dict(self.plan),
            "backend": self.backend,
            "warning": self.warning,
            "prior_evaluations": [dict(item) for item in self.prior_evaluations],
            "submitted": False,
            "execution_performed": False,
        }


class EvolutionCoordinator:
    """Connect cognitive planning, SQLite feedback memory, and the goal queue.

    Retrieved evaluations are review context only: they are not injected into model
    prompts and cannot change action permissions. The caller explicitly chooses when
    to queue a prepared plan. The autonomy engine remains the execution policy gate.
    """

    def __init__(
        self,
        engine: AutonomyEngine,
        planner: GoalPlanner | None = None,
        cognitive: CognitiveCore | None = None,
        learning: LearningStore | None = None,
    ) -> None:
        self.engine = engine
        self.planner = planner or GoalPlanner(engine)
        if self.planner.engine is not engine:
            raise ValueError("planner must be attached to the same AutonomyEngine")
        self.cognitive = cognitive or CognitiveCore(self.planner)
        if self.cognitive.planner is not self.planner:
            raise ValueError("cognitive core must use the coordinator's planner")
        self.learning = learning or LearningStore()

    def prepare(
        self, goal: str, *, allow_remote: bool = False, memory_limit: int = 5
    ) -> PreparedEvolution:
        """Plan and retrieve prior outcomes without queueing or executing anything."""
        if not 1 <= int(memory_limit) <= 20:
            raise ValueError("memory_limit must be between 1 and 20")
        prior = self.learning.retrieve(goal, limit=memory_limit)
        result = self.cognitive.plan(goal, allow_remote=allow_remote)
        return PreparedEvolution(
            plan=result.plan,
            backend=result.backend,
            warning=result.warning,
            prior_evaluations=tuple(prior),
        )

    def submit_for_review(self, prepared: PreparedEvolution) -> list[str]:
        """Persist proposed steps in the queue; this does not run an autonomy cycle."""
        if not isinstance(prepared, PreparedEvolution):
            raise TypeError("prepared must be a PreparedEvolution")
        return self.planner.submit_for_review(prepared.plan)

    def record_evaluation(
        self,
        goal: str,
        *,
        score: float,
        outcome: str,
        feedback: str = "",
        plan_summary: str = "",
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Record caller-provided feedback; no task success is inferred."""
        return self.learning.record(
            goal, score=score, outcome=outcome, feedback=feedback,
            plan_summary=plan_summary, tags=tags,
        )

    def learning_summary(self) -> dict[str, Any]:
        return self.learning.summary()

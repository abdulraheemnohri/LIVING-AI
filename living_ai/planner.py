"""Explainable goal decomposition for LIVING-AI.

This planner proposes registered action names and payloads; it does not execute tools,
call an LLM, access the network, or bypass AutonomyEngine policy gates.
"""
from __future__ import annotations

import re
import uuid
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class PlanStep:
    step_id: str
    title: str
    action: str
    payload: dict[str, Any]
    rationale: str
    requires_review: bool


@dataclass(frozen=True)
class Plan:
    plan_id: str
    goal: str
    steps: tuple[PlanStep, ...]
    created_for_review: bool = True


class GoalPlanner:
    """Conservative baseline planner: proposes notes for vague goals, never executes."""

    def __init__(self, engine: Any, *, max_steps: int = 5) -> None:
        if not 1 <= max_steps <= 10:
            raise ValueError("max_steps must be between 1 and 10")
        self.engine = engine
        self.max_steps = max_steps

    def plan(self, goal: str) -> Plan:
        goal = " ".join(str(goal).split())
        if not goal or len(goal) > 1000:
            raise ValueError("Goal must contain 1–1000 characters")
        # Deliberately deterministic and conservative until an evaluated model adapter exists.
        sentences = [s.strip(" .") for s in re.split(r"(?<=[.!?])\s+", goal) if s.strip(" .")]
        chunks = sentences[: self.max_steps] or [goal]
        steps = []
        for index, chunk in enumerate(chunks, 1):
            available = "save_note" in getattr(self.engine, "actions", {})
            steps.append(PlanStep(
                step_id=uuid.uuid4().hex,
                title=f"Record planning item {index}",
                action="save_note",
                payload={"text": f"Goal: {goal}\nPlanning item: {chunk}"},
                rationale="Conservative baseline records the goal for human review; it does not infer permission to perform external actions.",
                requires_review=True,
            ))
            if not available:
                # Keep the proposal visible; engine policy will hold the unknown action.
                steps[-1] = PlanStep(
                    step_id=steps[-1].step_id, title=steps[-1].title,
                    action="planner_note_unavailable", payload={"text": chunk},
                    rationale="The engine has no registered save_note action.",
                    requires_review=True,
                )
        return Plan(plan_id=uuid.uuid4().hex, goal=goal, steps=tuple(steps))

    def submit_for_review(self, plan: Plan) -> list[str]:
        """Queue proposed steps without running them; engine policy still controls execution."""
        ids = []
        for step in plan.steps:
            goal_id = self.engine.add_goal(
                title=f"[{plan.plan_id[:8]}] {step.title}",
                action=step.action,
                payload=step.payload,
            )
            # A submitted proposal is not approval. Hold it before any worker cycle.
            self.engine.require_approval(goal_id)
            ids.append(goal_id)
        return ids

    @staticmethod
    def to_dict(plan: Plan) -> dict[str, Any]:
        return {
            "plan_id": plan.plan_id,
            "goal": plan.goal,
            "created_for_review": plan.created_for_review,
            "steps": [asdict(step) for step in plan.steps],
        }

import json

from living_ai.autonomous import AutonomyEngine
from living_ai.cognitive import CognitiveCore
from living_ai.planner import GoalPlanner


def make_core(tmp_path, provider):
    engine = AutonomyEngine(tmp_path / "autonomy.sqlite3")
    return CognitiveCore(GoalPlanner(engine, max_steps=3), provider=provider), engine


def test_remote_disabled_does_not_call_provider(tmp_path):
    calls = []
    core, _ = make_core(tmp_path, lambda prompt: calls.append(prompt) or '{"steps":["x"]}')
    result = core.plan("Create a safe outline")
    assert result.backend == "deterministic"
    assert calls == []


def test_model_plan_is_bounded_review_only(tmp_path):
    core, engine = make_core(tmp_path, lambda prompt: json.dumps({"steps": ["Define scope", "List risks"]}))
    result = core.plan("Create a project plan", allow_remote=True)
    assert result.backend == "optional-compatible-provider"
    assert len(result.plan.steps) == 2
    assert all(step.action == "save_note" and step.requires_review for step in result.plan.steps)
    assert engine.list_goals() == []


def test_invalid_model_output_falls_back(tmp_path):
    core, _ = make_core(tmp_path, lambda prompt: '{"steps":["", 42]}')
    result = core.plan("Create a project plan", allow_remote=True)
    assert result.backend == "deterministic-fallback"
    assert result.plan.steps


def test_too_many_model_steps_fall_back(tmp_path):
    core, _ = make_core(tmp_path, lambda prompt: '{"steps":["a","b","c","d"]}')
    result = core.plan("Create a project plan", allow_remote=True)
    assert result.backend == "deterministic-fallback"


def test_submission_queues_without_execution(tmp_path):
    core, engine = make_core(tmp_path, lambda prompt: '{"steps":["Review risks"]}')
    result = core.plan("Prepare a plan", allow_remote=True)
    ids = core.submit_for_review(result)
    assert len(ids) == 1
    assert engine.list_goals()[0]["status"] == "needs_approval"
    assert engine.list_notes() == []

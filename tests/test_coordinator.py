import tempfile
from pathlib import Path

import pytest

from living_ai.autonomous import AutonomyEngine
from living_ai.cognitive import CognitiveCore
from living_ai.coordinator import EvolutionCoordinator, PreparedEvolution
from living_ai.learning import LearningStore
from living_ai.planner import GoalPlanner


@pytest.fixture
def coordinator(tmp_path):
    engine = AutonomyEngine(tmp_path / "autonomy.sqlite3")
    planner = GoalPlanner(engine)
    learning = LearningStore(tmp_path / "learning.sqlite3")
    cognitive = CognitiveCore(planner, provider=lambda _: None)
    return EvolutionCoordinator(engine, planner, cognitive, learning), engine


def test_prepare_retrieves_memory_without_queueing(coordinator):
    loop, engine = coordinator
    loop.record_evaluation(
        "write project tests", score=0.9, outcome="Tests passed",
        feedback="Use small isolated tests", tags=["testing"]
    )
    prepared = loop.prepare("write project tests")
    assert isinstance(prepared, PreparedEvolution)
    assert prepared.prior_evaluations
    assert engine.list_goals() == []
    assert prepared.to_dict()["execution_performed"] is False


def test_submit_queues_but_does_not_execute(coordinator):
    loop, engine = coordinator
    prepared = loop.prepare("make a project note")
    ids = loop.submit_for_review(prepared)
    assert len(ids) == len(prepared.plan.steps)
    assert all(item["status"] == "needs_approval" for item in engine.list_goals())
    assert engine.list_notes() == []


def test_evaluation_updates_summary_and_retrieval(coordinator):
    loop, _ = coordinator
    loop.record_evaluation(
        "improve offline search", score=0.8, outcome="Search improved",
        plan_summary="Add lexical retrieval", feedback="Keep it local"
    )
    assert loop.learning_summary()["evaluations"] == 1
    prepared = loop.prepare("improve offline search")
    assert prepared.prior_evaluations[0]["outcome"] == "Search improved"


def test_remote_planning_is_opt_in(coordinator):
    loop, _ = coordinator
    calls = []
    core = CognitiveCore(loop.planner, provider=lambda prompt: calls.append(prompt) or None)
    loop.cognitive = core
    result = loop.prepare("review this goal")
    assert result.backend == "deterministic"
    assert calls == []


def test_invalid_memory_limit_is_rejected(coordinator):
    loop, _ = coordinator
    with pytest.raises(ValueError):
        loop.prepare("goal", memory_limit=0)


def test_components_must_share_engine_and_planner(coordinator, tmp_path):
    loop, engine = coordinator
    other = AutonomyEngine(tmp_path / "other.sqlite3")
    with pytest.raises(ValueError):
        EvolutionCoordinator(engine, GoalPlanner(other), learning=loop.learning)

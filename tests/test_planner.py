from living_ai.autonomous import AutonomyEngine
from living_ai.planner import GoalPlanner


def test_planner_is_proposal_only(tmp_path):
    engine = AutonomyEngine(tmp_path / "state.sqlite3")
    planner = GoalPlanner(engine)
    plan = planner.plan("Build a local assistant. Test it.")
    assert plan.created_for_review
    assert len(plan.steps) == 2
    assert all(step.requires_review for step in plan.steps)
    assert engine.list_goals() == []


def test_submit_queues_without_execution(tmp_path):
    engine = AutonomyEngine(tmp_path / "state.sqlite3")
    planner = GoalPlanner(engine)
    plan = planner.plan("Prepare a project outline.")
    ids = planner.submit_for_review(plan)
    assert len(ids) == 1
    assert engine.list_goals()[0]["status"] == "queued"
    assert engine.list_notes() == []


def test_empty_and_oversized_goals_rejected(tmp_path):
    planner = GoalPlanner(AutonomyEngine(tmp_path / "state.sqlite3"))
    for goal in ("", "   "):
        try:
            planner.plan(goal)
            assert False, "expected ValueError"
        except ValueError:
            pass
    try:
        planner.plan("x" * 1001)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_plan_size_is_bounded(tmp_path):
    planner = GoalPlanner(AutonomyEngine(tmp_path / "state.sqlite3"), max_steps=2)
    plan = planner.plan("One. Two. Three.")
    assert len(plan.steps) == 2

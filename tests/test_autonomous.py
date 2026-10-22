from living_ai.autonomous import Action, AutonomyEngine

def test_reversible_goal_runs_and_is_audited(tmp_path):
    engine = AutonomyEngine(tmp_path / "autonomy.sqlite3")
    gid = engine.add_goal("Save idea", "save_note", {"text": "Build a planner"})
    result = engine.cycle()
    assert result[0]["goal_id"] == gid and result[0]["status"] == "completed"
    assert engine.list_notes()[0]["body"] == "Build a planner"
    assert engine.list_runs()[0]["outcome"] == "completed"

def test_unknown_action_is_held(tmp_path):
    engine = AutonomyEngine(tmp_path / "autonomy.sqlite3")
    gid = engine.add_goal("Unknown", "unknown_action", {})
    assert engine.cycle()[0]["status"] == "needs_approval"
    assert engine.approve_goal(gid)
    assert engine.cycle()[0]["status"] == "needs_approval"

def test_non_reversible_action_never_auto_runs(tmp_path):
    engine = AutonomyEngine(tmp_path / "autonomy.sqlite3")
    engine.register_action(Action("dangerous", lambda _: {"ok": True}, reversible=False))
    engine.add_goal("Danger", "dangerous", {})
    assert engine.cycle()[0]["status"] == "needs_approval"

def test_cycle_is_bounded(tmp_path):
    engine = AutonomyEngine(tmp_path / "autonomy.sqlite3", max_actions_per_cycle=2)
    for i in range(5):
        engine.add_goal(f"Note {i}", "save_note", {"text": str(i)})
    assert len(engine.cycle()) == 2
    assert sum(g["status"] == "queued" for g in engine.list_goals()) == 3

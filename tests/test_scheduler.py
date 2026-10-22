from living_ai.scheduler import AutonomyScheduler


class FakeEngine:
    def __init__(self):
        self.calls = 0

    def cycle(self):
        self.calls += 1
        return [{"cycle": self.calls}]


def test_scheduler_starts_paused_and_does_not_run(tmp_path):
    engine = FakeEngine()
    scheduler = AutonomyScheduler(engine, interval_seconds=5)
    assert scheduler.tick()["status"] == "paused"
    assert engine.calls == 0


def test_scheduler_waits_for_interval():
    now = [10.0]
    engine = FakeEngine()
    scheduler = AutonomyScheduler(engine, interval_seconds=5, max_cycles_per_run=2, clock=lambda: now[0])
    scheduler.resume()
    assert scheduler.tick()["status"] == "ran"
    assert scheduler.tick()["status"] == "waiting"
    now[0] += 5
    assert scheduler.tick()["status"] == "ran"
    assert engine.calls == 2
    assert scheduler.paused


def test_force_bypasses_only_interval():
    now = [0.0]
    engine = FakeEngine()
    scheduler = AutonomyScheduler(engine, interval_seconds=5, max_cycles_per_run=3, clock=lambda: now[0])
    scheduler.resume()
    assert scheduler.tick()["status"] == "ran"
    assert scheduler.tick(force=True)["status"] == "ran"
    assert engine.calls == 2


def test_disable_and_enable_do_not_resume_automatically():
    engine = FakeEngine()
    scheduler = AutonomyScheduler(engine)
    scheduler.resume()
    scheduler.disable()
    assert scheduler.tick()["status"] == "disabled"
    scheduler.enable()
    assert scheduler.tick()["status"] == "paused"
    assert engine.calls == 0


def test_cycle_budget_pauses_scheduler():
    engine = FakeEngine()
    scheduler = AutonomyScheduler(engine, max_cycles_per_run=1)
    scheduler.resume()
    result = scheduler.tick()
    assert result["status"] == "ran" and result["paused"] is True
    assert scheduler.status()["cycles_completed"] == 1
    scheduler.reset_run_budget()
    assert scheduler.status()["cycles_completed"] == 0
    assert scheduler.paused

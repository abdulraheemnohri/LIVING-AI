"""Opt-in, resource-bounded scheduler for the LIVING-AI autonomy engine.

The scheduler never starts itself at import time. Call tick() from a host loop or run()
explicitly from a CLI/service entry point.
"""
from __future__ import annotations

import time
from typing import Any


class AutonomyScheduler:
    def __init__(
        self,
        engine: Any,
        *,
        interval_seconds: float = 60.0,
        max_cycles_per_run: int = 1,
        clock=time.monotonic,
    ) -> None:
        if interval_seconds < 1:
            raise ValueError("interval_seconds must be at least 1 second")
        if not 1 <= max_cycles_per_run <= 10:
            raise ValueError("max_cycles_per_run must be between 1 and 10")
        self.engine = engine
        self.interval_seconds = float(interval_seconds)
        self.max_cycles_per_run = int(max_cycles_per_run)
        self._clock = clock
        self._last_run: float | None = None
        self._paused = True
        self._enabled = True
        self._cycles = 0

    @property
    def paused(self) -> bool:
        return self._paused

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def cycles_completed(self) -> int:
        return self._cycles

    def resume(self) -> None:
        if self._enabled:
            self._paused = False

    def pause(self) -> None:
        self._paused = True

    def disable(self) -> None:
        self._enabled = False
        self._paused = True

    def enable(self) -> None:
        self._enabled = True
        # Enabling does not implicitly resume execution.
        self._paused = True

    def status(self) -> dict[str, Any]:
        return {
            "enabled": self._enabled,
            "paused": self._paused,
            "interval_seconds": self.interval_seconds,
            "max_cycles_per_run": self.max_cycles_per_run,
            "cycles_completed": self._cycles,
            "seconds_until_due": self._seconds_until_due(),
        }

    def _seconds_until_due(self) -> float:
        if self._last_run is None:
            return 0.0
        return max(0.0, self.interval_seconds - (self._clock() - self._last_run))

    def tick(self, *, force: bool = False) -> dict[str, Any]:
        """Run at most one bounded engine cycle when enabled, resumed, and due.

        force bypasses only the interval check; it never bypasses pause/disable policy.
        """
        if not self._enabled:
            return {"status": "disabled", "results": []}
        if self._paused:
            return {"status": "paused", "results": []}
        if not force and self._seconds_until_due() > 0:
            return {"status": "waiting", "results": [],
                    "seconds_until_due": round(self._seconds_until_due(), 2)}
        if self._cycles >= self.max_cycles_per_run:
            self.pause()
            return {"status": "cycle_limit_reached", "results": []}
        results = self.engine.cycle()
        self._last_run = self._clock()
        self._cycles += 1
        if self._cycles >= self.max_cycles_per_run:
            self.pause()
        return {"status": "ran", "cycle": self._cycles, "results": results,
                "paused": self._paused}

    def reset_run_budget(self) -> None:
        """Reset the per-run cycle budget; leaves scheduler paused for safe restart."""
        self._cycles = 0
        self._last_run = None
        self.pause()

"""Balance-recovery detection after a perturbation (docs/DECISIONS.md D7).

The scheduler only needs "has the subject recovered yet?". Any detector implementing
`RecoveryDetector` can be plugged in.

TODO(recovery): insert the lab's algorithm here (gait prediction + whole-body angular
momentum). Wrap it in a class implementing `RecoveryDetector`, then pass it to
`experiment.Scheduler(recovery=...)`. Open points before wiring it (docs/STATUS.md):
language (Python / MATLAB), inputs (markers/segments, rate), output (flag / score /
timestamp), per-update latency. `frame` below is whatever `vicon.stream()` yields once
marker streaming exists; its type is not fixed yet.
"""
from __future__ import annotations

from typing import Any, Protocol


class RecoveryDetector(Protocol):
    def start(self, t_s: float) -> None:
        """Called when a perturbation is sent. Reset internal state."""

    def update(self, t_s: float, frame: Any = None) -> bool:
        """Called every Vicon frame after `start`. Return True once balance is recovered."""


class FixedWaitRecovery:
    """STAND-IN, not a recovery criterion: 'recovered' = `wait_s` seconds after the perturbation.
    Replace with the lab algorithm (see TODO above). `wait_s` has no default on purpose."""

    def __init__(self, wait_s: float):
        if wait_s < 0:
            raise ValueError("wait_s must be >= 0")
        self.wait_s = wait_s
        self._t0: float | None = None

    def start(self, t_s: float) -> None:
        self._t0 = t_s

    def update(self, t_s: float, frame: Any = None) -> bool:
        return self._t0 is not None and t_s - self._t0 >= self.wait_s

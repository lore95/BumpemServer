"""Perturbation scheduling. Port of legacy/MATLAB_script.m (lines 10-17, 47, 97-107)."""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

from .gait import FS_VALID
from .recovery import RecoveryDetector


def make_sequence(cmds=("a", "b", "c", "ab", "bc"), n_blocks=5, rng=random) -> list[str]:
    """n_blocks shuffled blocks of cmds (each direction appears once per block)."""
    seq: list[str] = []
    for _ in range(n_blocks):
        block = list(cmds)
        rng.shuffle(block)
        seq += block
    return seq


@dataclass
class Scheduler:
    sequence: list[str]
    fs_min: int = 50
    fs_max: int = 75
    rng: random.Random = field(default_factory=random.Random)
    done: int = 0
    fs_since_last: int = 0
    fs_target: int = 0
    # None = count FS from the last perturbation (MATLAB behavior).
    # Set = count FS only after the detector reports recovery (D7). TODO(recovery): lab algorithm.
    recovery: RecoveryDetector | None = None
    recovered: bool = True

    def __post_init__(self):
        self.fs_target = self.rng.randint(self.fs_min, self.fs_max)  # inclusive, like randi

    @property
    def finished(self) -> bool:
        return self.done >= len(self.sequence)

    def observe(self, t_s: float, frame: Any = None) -> None:
        """Call every Vicon frame. Feeds the recovery detector while waiting for recovery."""
        if self.recovery is not None and not self.recovered:
            self.recovered = self.recovery.update(t_s, frame)

    def on_event(self, event: str, t_s: float | None = None) -> str | None:
        """Call with every gait event. Returns a command to send, or None.
        `t_s` is required when a recovery detector is set."""
        if event != FS_VALID or self.finished:
            return None
        if self.recovery is not None:
            if t_s is None:
                raise ValueError("t_s required with a recovery detector")
            self.observe(t_s)
            if not self.recovered:
                return None
        self.fs_since_last += 1
        if self.fs_since_last < self.fs_target:
            return None
        cmd = self.sequence[self.done]
        self.done += 1
        self.fs_since_last = 0
        self.fs_target = self.rng.randint(self.fs_min, self.fs_max)
        if self.recovery is not None:
            self.recovery.start(t_s)
            self.recovered = False
        return cmd

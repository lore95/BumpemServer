"""Foot-strike / toe-off detection. Exact port of legacy/MATLAB_script.m (lines 83-125).

Feed one sample at a time: event = det.update(t_s, fz_total).
"""
from __future__ import annotations

from dataclasses import dataclass, field

FS_VALID, FS_NOISE, TO_VALID, TO_NOISE = "FS_VALID", "FS_NOISE", "TO_VALID", "TO_NOISE"


@dataclass
class GaitParams:
    fz_threshold: float = 250.0     # N        (MATLAB :5)
    min_gait_cycle: float = 0.30    # s        (MATLAB :6)
    min_stance: float = 0.15        # s        (MATLAB :7)
    min_since_to: float = 0.10      # s        (MATLAB :89, hardcoded)


@dataclass
class GaitDetector:
    p: GaitParams = field(default_factory=GaitParams)
    in_stance: bool = False
    prev_fz: float = 0.0
    last_fs: float = float("-inf")
    last_to: float = float("-inf")
    stance_start: float = float("-inf")
    fs_count: int = 0

    def update(self, t: float, fz: float) -> str:
        mag, mag_prev, th = abs(fz), abs(self.prev_fz), self.p.fz_threshold
        event = ""
        if not self.in_stance and mag_prev < th and mag >= th:
            if t - self.last_fs >= self.p.min_gait_cycle and t - self.last_to > self.p.min_since_to:
                self.in_stance, self.stance_start, self.last_fs = True, t, t
                self.fs_count += 1
                event = FS_VALID
            else:
                event = FS_NOISE
        # MATLAB runs the TO check in the same iteration (after FS); preserved.
        if self.in_stance and mag_prev >= th and mag < th:
            if t - self.stance_start >= self.p.min_stance:
                self.in_stance, self.last_to = False, t
                event = TO_VALID
            else:
                event = TO_NOISE
        self.prev_fz = fz
        return event

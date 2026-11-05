"""Foot-strike / toe-off detection. GaitDetector: exact port of legacy/MATLAB_script.m (lines 83-125).
ContactDetector + fit_thresholds: per-plate touch-down / foot-off as scripts/Pertubation_analog/AAPertAnalogTrig_SLAP.m (study, D45).

Feed one sample at a time: event = det.update(t_s, fz_total).
"""
from __future__ import annotations

import statistics
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


TD, FO = "TD", "FO"
SLAP_TD_N, SLAP_FO_N = 100.0, 25.0        # AAPertAnalogTrig_SLAP.m dataCapture: TD = 100, FO = 25 (N)
MIN_TD_N, MIN_FO_N = 20.0, 10.0           # lowest thresholds above the swing mean (fit_thresholds)
TD_SD, FO_SD = 6.0, 3.0                   # ... or this many swing-noise SDs, whichever is larger
EDGE_S = 0.03                             # swing samples this close to a contact are left out of the noise


@dataclass
class ContactDetector:
    """Touch-down / foot-off on one plate with hysteresis: port of scripts/Pertubation_analog/AAPertAnalogTrig_SLAP.m
    (dataCapture): the first touch-down only after the force was below `td_n`, then TD when Fz rises above `td_n`,
    FO when it falls below `fo_n`. Difference: every sample is checked; the script returned after the first event of
    each 100 ms block, so a foot-off in the same block as its touch-down was found a block late."""
    td_n: float = SLAP_TD_N
    fo_n: float = SLAP_FO_N
    in_contact: bool | None = None            # None: waiting for the force to drop below td_n (script: start = 0)

    def update(self, t: float, fz: float) -> str:
        if self.in_contact is None:
            if fz < self.td_n:
                self.in_contact = False
            return ""
        if not self.in_contact and fz > self.td_n:
            self.in_contact = True
            return TD
        if self.in_contact and fz < self.fo_n:
            self.in_contact = False
            return FO
        return ""


def contacts(t: list[float], fz: list[float], td_n: float, fo_n: float) -> list[tuple[str, float]]:
    d = ContactDetector(td_n, fo_n)
    return [(e, ti) for ti, f in zip(t, fz) if (e := d.update(ti, f))]


def fit_thresholds(t: list[float], fz: list[float]) -> dict:
    """Lowest stable thresholds for one plate (docs/API.md "Study"): swing noise (between foot-off and the next
    touch-down found with the script's 100 / 25 N, EDGE_S from each) → td = mean + max(TD_SD sd, MIN_TD_N),
    fo = mean + max(FO_SD sd, MIN_FO_N), never above 100 / 25 N. Kept (`stable`) only if they find the same number of
    touch-downs as 100 / 25 N (± 1); else 100 / 25 N. Returns td_n, fo_n, noise_mean_n, noise_sd_n, stable, events."""
    ev = contacts(t, fz, SLAP_TD_N, SLAP_FO_N)
    swing = []
    for (k1, t1), (k2, t2) in zip(ev, ev[1:]):
        if k1 == FO and k2 == TD:
            swing += [f for ti, f in zip(t, fz) if t1 + EDGE_S <= ti <= t2 - EDGE_S]
    out = {"td_n": SLAP_TD_N, "fo_n": SLAP_FO_N, "noise_mean_n": None, "noise_sd_n": None, "stable": False, "events": ev}
    if len(swing) < 100:
        return out
    mu, sd = statistics.fmean(swing), statistics.pstdev(swing)
    td = min(SLAP_TD_N, mu + max(TD_SD * sd, MIN_TD_N))
    fo = min(SLAP_FO_N, mu + max(FO_SD * sd, MIN_FO_N), td - 5)
    new = contacts(t, fz, td, fo)
    n_old, n_new = sum(k == TD for k, _ in ev), sum(k == TD for k, _ in new)
    out.update(noise_mean_n=round(mu, 2), noise_sd_n=round(sd, 2))
    if abs(n_new - n_old) <= 1:
        out.update(td_n=round(td, 1), fo_n=round(fo, 1), stable=True, events=new)
    return out

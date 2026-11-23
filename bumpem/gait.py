"""Foot-strike / toe-off detection. GaitDetector: exact port of legacy/MATLAB_script.m (lines 83-125).
ContactDetector + fit_thresholds: per-plate touch-down / foot-off as scripts/Pertubation_analog/AAPertAnalogTrig_SLAP.m (study, D45).
RunningDetector: running, touch-down / foot-off on the sum of both belts, side from the weight shift (D57).

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


TD_BW, FO_BW = 0.25, 0.10                 # running: touch-down / foot-off on the belt sum, fraction of body weight (D57)
SIDE_S = 0.02                             # running: a touch-down counts, and gets its side, this long after it
SIDE_SHIFT = 0.15                         # running: change of the left-belt share that decides the side


@dataclass
class RunningDetector:
    """Running (D57): contacts on the sum of both belts, as legacy/MATLAB_script.m (Fz_total): a flight phase between
    every step, so a foot on the other belt or across the middle is still one contact. A touch-down counts once the sum
    stays above `fo_n` for SIDE_S (shorter = noise); its side from the share of the force on the left belt over that
    time: up by more than SIDE_SHIFT against the previous contact = left, down = right, else the opposite of the
    previous side (running alternates). Assumes the left foot lands further left than the right one.

    update(t, left, right) → [(TD | FO, "left" | "right", event time)]; a touch-down carries its own sample time."""
    td_n: float
    fo_n: float
    in_contact: bool | None = None            # None: waiting for the sum to drop below td_n
    t_td: float = 0.0
    sum_left: float = 0.0
    sum_all: float = 0.0
    side: str | None = None                   # current contact's side, once decided
    prev_share: float | None = None
    prev_side: str | None = None

    @classmethod
    def for_mass(cls, mass_kg: float) -> "RunningDetector":
        bw = mass_kg * 9.81
        return cls(round(TD_BW * bw, 1), round(FO_BW * bw, 1))

    def reset(self) -> "RunningDetector":
        return RunningDetector(self.td_n, self.fo_n)

    def update(self, t: float, left: float, right: float) -> list[tuple[str, str, float]]:
        f = left + right
        if self.in_contact is None:
            if f < self.td_n:
                self.in_contact = False
            return []
        if not self.in_contact:
            if f <= self.td_n:
                return []
            self.in_contact, self.t_td, self.sum_left, self.sum_all, self.side = True, t, 0.0, 0.0, None
        if f < self.fo_n:
            self.in_contact = False
            return [(FO, self.side, t)] if self.side else []
        if self.side is None:
            self.sum_left += left
            self.sum_all += f
            if t - self.t_td >= SIDE_S:
                share = self.sum_left / self.sum_all
                d = None if self.prev_share is None else share - self.prev_share
                if d is None:
                    self.side = "left" if share > 0.5 else "right"
                elif abs(d) > SIDE_SHIFT:
                    self.side = "left" if d > 0 else "right"
                else:
                    self.side = "right" if self.prev_side == "left" else "left"
                self.prev_share, self.prev_side = share, self.side
                return [(TD, self.side, self.t_td)]
        return []


def running_contacts(t: list[float], left: list[float], right: list[float], td_n: float, fo_n: float) -> list[tuple[str, str, float]]:
    d = RunningDetector(td_n, fo_n)
    return [e for ti, a, b in zip(t, left, right) for e in d.update(ti, a, b)]

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


CONFIRM_S = 0.005                         # walking: a touch-down counts once the plate stays above td_n this long (D60)
SWING_MIN_S = 0.15                        # walking: a rise this soon after the plate's foot-off is the same contact
RESTRIKE_BW, RESTRIKE_S = 0.30, 0.03      # walking: rise of this share of body weight within this time on a loaded plate
SETTLE_S = 0.15                           #          = a second foot landing on it; not within this time of its touch-down


@dataclass
class _Plate:
    td_n: float
    fo_n: float
    in_contact: bool | None = None            # None: waiting for the force to drop below td_n
    side: str = ""                            # foot on the plate (its own side, or the other after a re-strike)
    t_td: float = float("-inf")
    t_fo: float = float("-inf")
    t_up: float | None = None                 # first sample above td_n, not yet confirmed
    hist: list = field(default_factory=list)  # (t, fz) of the last RESTRIKE_S


@dataclass
class WalkingDetector:
    """Walking (D60): each plate as ContactDetector (touch-down above td_n, foot-off below fo_n), plus
    - a touch-down counts after CONFIRM_S above td_n (noise spikes near a low fitted threshold are no step), and not
      within SWING_MIN_S of that plate's foot-off (the force bouncing around fo_n: the contact goes on, no event);
    - re-strike: a foot landing across the middle keeps the other belt loaded, so that plate never reaches foot-off and
      the next foot landing on it would be missed. A rise of RESTRIKE_BW body weight within RESTRIKE_S on a plate in
      contact (SETTLE_S after its touch-down) is a touch-down; its side from the alternation (opposite of the last one).
    Thresholds from 2026-11-19 walking (1.7 m/s): alternation breaks 143 → 2, no extra steps on the clean replay.

    update(t, left, right) → [(TD | FO, "left" | "right", event time)]."""
    mass_kg: float
    plates: dict = field(default_factory=dict)
    last_side: str | None = None
    restrikes: int = 0                        # touch-downs found by re-strike
    breaks: int = 0                           # touch-downs on the same side twice in a row (a step missed)

    def __post_init__(self):
        if not self.plates:
            self.plates = {s: _Plate(SLAP_TD_N, SLAP_FO_N) for s in ("left", "right")}

    def set_thresholds(self, side: str, td_n: float, fo_n: float) -> None:
        """New thresholds for one plate; it waits for its force to drop below td_n again."""
        self.plates[side] = _Plate(td_n, fo_n)

    def reset(self) -> "WalkingDetector":
        return WalkingDetector(self.mass_kg, {s: _Plate(p.td_n, p.fo_n) for s, p in self.plates.items()})

    def _td(self, side: str, t: float) -> tuple[str, str, float]:
        if side == self.last_side:
            self.breaks += 1
        self.last_side = side
        return (TD, side, t)

    def update(self, t: float, left: float, right: float) -> list[tuple[str, str, float]]:
        out = []
        for plate, f in (("left", left), ("right", right)):
            p = self.plates[plate]
            p.hist.append((t, f))
            while p.hist[0][0] < t - RESTRIKE_S:
                p.hist.pop(0)
            if p.in_contact is None:
                if f < p.td_n:
                    p.in_contact = False
                continue
            if not p.in_contact:
                if f <= p.td_n:
                    p.t_up = None
                    continue
                if p.t_up is None:
                    p.t_up = t
                if t - p.t_up < CONFIRM_S:
                    continue
                p.in_contact, p.t_td = True, p.t_up
                if p.t_up - p.t_fo < SWING_MIN_S:            # bounce after foot-off: the same contact, a re-strike may follow
                    p.t_td -= SETTLE_S
                    continue
                p.side = plate
                out.append(self._td(plate, p.t_up))
            elif f < p.fo_n:
                p.in_contact, p.t_fo, p.t_up = False, t, None
                if p.side:
                    out.append((FO, p.side, t))
            elif t - p.t_td >= SETTLE_S and f - min(x for _, x in p.hist) > RESTRIKE_BW * self.mass_kg * 9.81:
                side = {"left": "right", "right": "left"}.get(self.last_side, plate)
                p.t_td, p.side = t, side
                self.restrikes += 1
                out.append(self._td(side, t))
        return out


def walking_contacts(t: list[float], left: list[float], right: list[float], mass_kg: float,
                     thresholds: dict | None = None) -> list[tuple[str, str, float]]:
    d = WalkingDetector(mass_kg)
    for side, (td, fo) in (thresholds or {}).items():
        d.set_thresholds(side, td, fo)
    return [e for ti, a, b in zip(t, left, right) for e in d.update(ti, a, b)]


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

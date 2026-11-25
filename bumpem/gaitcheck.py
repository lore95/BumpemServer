"""Gait check (docs/API.md "Gait check", D58): touch-down, foot-off and phase moments live from the Vicon plates, no
board, for checking the detection against a high-speed video of the participant and the screen. Same detectors as the
study: walking per plate (thresholds from the first FIT_S of swing noise, as the gait pattern), running on the belt sum
(D57).

The server feeds plate samples (`on_samples`, Vicon frame clock); `publish` gets each stream item, `log` the events-file
row. Phase moments fire from timer threads.
"""
from __future__ import annotations

import statistics
import threading
from typing import Any, Callable, Literal

from pydantic import BaseModel, Field

from .gait import FO, TD, RunningDetector, WalkingDetector, fit_thresholds

SIDES = ("left", "right")
FIT_S = 10.0          # walking: swing noise of the first 10 s sets the thresholds
KEEP = 10             # strides / contacts per side for the phase and the status
MIN_N = 3             # strides needed before phase moments


class GaitCheckBody(BaseModel):
    mode: Literal["walking", "running"] = "walking"
    mass_kg: float = Field(gt=0, le=300)
    trigger_side: Literal["left", "right", "any"] = "left"
    gait_phase_pct: float = Field(20, ge=0, lt=100)
    gait_phase_of: Literal["stance", "cycle"] = "cycle"


def _strides(td: list[float]) -> list[float]:
    d = [b - a for a, b in zip(td, td[1:])]
    if not d:
        return d
    m = statistics.median(d)
    return [x for x in d if 0.5 * m <= x <= 1.5 * m]       # missed or extra touch-downs left out (as the gait pattern)


class GaitCheck:
    def __init__(self, cfg: GaitCheckBody, plates: dict[str, str], publish: Callable[[dict], None],
                 log: Callable[[str, dict], None], to_pc: Callable[[float], float | None], now: Callable[[], float]):
        self.cfg, self.plates = cfg, plates
        self._publish, self._log, self._to_pc, self._now = publish, log, to_pc, now
        self._lock = threading.RLock()
        self._run = RunningDetector.for_mass(cfg.mass_kg) if cfg.mode == "running" else None
        self._walk = WalkingDetector(cfg.mass_kg)                        # walking (D60)
        self._rec: dict[str, tuple[list[float], list[float]]] | None = None if self._run else {s: ([], []) for s in SIDES}
        self._t0: float | None = None
        self.running, self.message, self.steps = True, None, 0
        self._td: dict[str, list[float]] = {s: [] for s in SIDES}        # touch-down times (plate clock)
        self._ct: dict[str, list[float]] = {s: [] for s in SIDES}        # contact times, s
        self._open: dict[str, float | None] = {s: None for s in SIDES}   # current contact's touch-down
        self._timers: list[threading.Timer] = []

    # --- status ---
    def status(self) -> dict[str, Any]:
        with self._lock:
            th = ({s: {"td_n": self._run.td_n, "fo_n": self._run.fo_n} for s in SIDES} if self._run else
                  {s: {"td_n": self._walk.plates[s].td_n, "fo_n": self._walk.plates[s].fo_n} for s in SIDES})
            out = {"running": self.running, "message": self.message, **self.cfg.model_dump(),
                   "detector": "plates" if self._run is None else "sum", "fitted": self._rec is None, "thresholds": th,
                   "steps": self.steps, "plates": self.plates,
                   "restrikes": None if self._run else self._walk.restrikes,
                   "alternation_breaks": None if self._run else self._walk.breaks}
            for s in SIDES:
                d, c = _strides(self._td[s]), self._ct[s]
                out[s] = {"stride_ms": round(statistics.fmean(d) * 1000, 1) if d else None,
                          "stride_sd_ms": round(statistics.pstdev(d) * 1000, 1) if d else None,
                          "contact_ms": round(statistics.fmean(c) * 1000, 1) if c else None, "n": len(d)}
            return out

    def _emit(self, item: dict) -> None:
        item = {"type": "gaitcheck", **item}
        self._publish(item)
        self._log("GAITCHECK", item)

    def _status_changed(self) -> None:
        self._emit({"event": "STATUS", **self.status()})

    def stop(self, message: str | None = None) -> None:
        with self._lock:
            if not self.running:
                return
            self.running, self.message = False, message
            for tm in self._timers:
                tm.cancel()
            self._timers = []
        self._status_changed()

    # --- plate samples (Vicon thread) ---
    def on_samples(self, samples: list[tuple[float, dict[str, float]]], host_s: float) -> None:
        if not samples or not self.running:
            return
        t_end = samples[-1][0]
        fitted = False
        with self._lock:
            for t, fz in samples:
                if self._t0 is None:
                    self._t0 = t
                v = [fz.get(self.plates[s]) for s in SIDES]
                if None in v:
                    continue
                if self._run is not None:
                    ev = self._run.update(t, *v)
                else:
                    ev = self._walk.update(t, *v)
                    rec = self._rec
                    if rec is not None:
                        for s, x in zip(SIDES, v):
                            rec[s][0].append(t)
                            rec[s][1].append(x)
                        if t - self._t0 >= FIT_S:
                            self._fit()
                            fitted = True
                for e, s, te in ev:
                    self._event(e, s, te, t_end, host_s)
        if fitted:
            self._status_changed()

    def _fit(self) -> None:
        rec, self._rec = self._rec, None
        bad = []
        for s in SIDES:
            f = fit_thresholds(*rec[s])
            if f["stable"]:
                self._walk.set_thresholds(s, f["td_n"], f["fo_n"])
                self._open[s] = None              # the new detector waits for the force to drop first
            else:
                bad.append(s)
        if bad:
            self.message = f"low thresholds unstable on {', '.join(bad)}: 100 / 25 N kept there"

    def _event(self, kind: str, side: str, t: float, t_end: float, host_s: float) -> None:
        pc = self._to_pc(t)
        if pc is None:                            # clock not fitted yet: from the frame's arrival
            pc = host_s - (t_end - t)
        if kind == FO:
            t_td, self._open[side] = self._open[side], None
            if t_td is None:
                return
            self._ct[side] = (self._ct[side] + [t - t_td])[-KEEP:]
            self._emit({"event": "FO", "side": side, "t_pc": round(pc, 4), "contact_ms": round((t - t_td) * 1000, 1)})
            return
        prev = self._td[side][-1] if self._td[side] else None
        self._td[side] = (self._td[side] + [t])[-(KEEP + 1):]
        self._open[side] = t
        self.steps += 1
        self._emit({"event": "TD", "side": side, "t_pc": round(pc, 4), "step": self.steps,
                    "stride_ms": None if prev is None else round((t - prev) * 1000, 1)})
        if self.cfg.trigger_side in ("any", side):
            self._phase(side, pc)

    def _phase(self, side: str, pc: float) -> None:
        d, c = _strides(self._td[side]), self._ct[side]
        if len(d) < MIN_N or (self.cfg.gait_phase_of == "stance" and len(c) < MIN_N):
            return
        stride = statistics.fmean(d) * 1000
        base = stride if self.cfg.gait_phase_of == "cycle" else statistics.fmean(c) * 1000
        phase = self.cfg.gait_phase_pct / 100 * base
        delay, nxt = phase - (self._now() - pc) * 1000, 0
        while delay < 0:                          # too late for this contact: same phase of the side's next one
            delay, nxt = delay + stride, nxt + 1
        item = {"event": "PHASE", "side": side, "t_pc": round(pc + (phase + nxt * stride) / 1000, 4),
                "phase_ms": round(phase, 1), "next_contact": nxt}
        tm = threading.Timer(delay / 1000, self._fire, (item,))
        tm.daemon = True
        self._timers = [x for x in self._timers if x.is_alive()] + [tm]
        tm.start()

    def _fire(self, item: dict) -> None:
        with self._lock:
            if not self.running:
                return
        self._emit({**item, "sent_pc": round(self._now(), 4)})

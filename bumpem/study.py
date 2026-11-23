"""Study runner (docs/API.md "Study", DECISIONS D44, D45): one subject + blocks, touch-down / foot-off per belt from
the Vicon plates (as scripts/Pertubation_analog/AAPertAnalogTrig_SLAP.m; running: on the sum of both belts, D57), each perturbation at a phase of the stance
(or stride) after a touch-down of the trigger side.

Pure logic: the server feeds plate samples (`on_samples`, Vicon frame clock) and gives it `send` (one perturbation → pulse id),
`publish` (stream item) and `log` (events-file row). Thread-safe: samples come from the Vicon thread, commands from
HTTP requests.
"""
from __future__ import annotations

import random
import statistics
import threading
from typing import Any, Callable, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .gait import FO, TD, ContactDetector, RunningDetector, fit_thresholds, running_contacts

G = 9.81
MIN_STRIDES = 5          # per side, for a gait pattern
SIDES = ("left", "right")
# plausible gait pattern per mode (D50): stride s, contact s; outside → message (wrong mode, plates, or not steady)
MODE_LIMITS = {"walking": {"stride": (0.7, 1.8), "contact": (0.35, 1.5)},
               "running": {"stride": (0.45, 1.0), "contact": (0.08, 0.4)}}


class Subject(BaseModel):
    model_config = ConfigDict(extra="allow")
    subject_id: str = Field("", pattern=r"^[A-Za-z0-9_-]{0,40}$", description="ID in the lab's master file, never a name (D53)")
    study_name: str = Field("", pattern=r"^[A-Za-z0-9 _-]{0,40}$", description="part of the session zip name (D53)")
    mass_kg: float = Field(gt=0, le=300)
    mode: Literal["walking", "running"] = "walking"
    baseline_n: float | None = Field(None, ge=0, le=50, description="rope tension between pulls; set before Arm")


class Block(BaseModel):
    model_config = ConfigDict(extra="allow")
    label: str = ""
    speed_ms: float = Field(gt=0, le=10)
    duration_s: float | None = Field(None, ge=10, le=7200, description="block ends at this or the last perturbation")
    warmup_s: float = Field(0, ge=0, le=3600)
    n_perturbations: int = Field(ge=1, le=500)
    pattern: str | None = Field(None, description="saved pattern (D50): directions + step gaps")
    pattern_items: list[dict[str, Any]] | None = Field(None, description="filled in by the server from `pattern`")
    directions_deg: list[float] | None = Field(None, min_length=1)
    amplitude_mode: Literal["newton", "percent_bw"] | None = None
    amplitude: float | None = Field(None, gt=0)
    intensity_pct_bw: float | None = Field(None, gt=0, le=100, description="legacy = percent_bw")
    phase1_ms: float = Field(ge=0)
    dur_ms: float = Field(gt=0)
    phase2_ms: float = Field(ge=0)
    trigger_side: Literal["left", "right", "any"]
    gait_phase_pct: float = Field(ge=0, lt=100)
    gait_phase_of: Literal["stance", "cycle"] = "cycle"
    timing_mode: Literal["random", "predefined"] | None = None
    interval_min_steps: int | None = Field(None, ge=1, le=1000)
    interval_max_steps: int | None = Field(None, ge=1, le=1000)
    schedule_steps: list[int] | None = None

    @model_validator(mode="after")
    def _timing(self):
        if self.phase1_ms + self.phase2_ms > self.dur_ms:
            raise ValueError("phase1_ms + phase2_ms longer than dur_ms")
        if self.amplitude_mode is None and self.intensity_pct_bw is None:
            raise ValueError("amplitude_mode + amplitude (or intensity_pct_bw) needed")
        if self.amplitude_mode is not None and self.amplitude is None:
            raise ValueError("amplitude needed with amplitude_mode")
        if self.amplitude_mode == "percent_bw" and self.amplitude > 100:
            raise ValueError("amplitude above 100 % body weight")
        if self.pattern or self.pattern_items:
            return self                            # directions and gaps from the pattern (length checked at load)
        if not self.directions_deg or self.timing_mode is None:
            raise ValueError("a pattern, or directions_deg + timing_mode, needed")
        if self.timing_mode == "random":
            if self.interval_min_steps is None or self.interval_max_steps is None:
                raise ValueError("random timing needs interval_min_steps and interval_max_steps")
            if self.interval_max_steps < self.interval_min_steps:
                raise ValueError("interval_max_steps below interval_min_steps")
        else:
            s = self.schedule_steps or []
            if len(s) != self.n_perturbations:
                raise ValueError(f"schedule_steps has {len(s)} steps for {self.n_perturbations} perturbations")
            if any(x < 1 for x in s) or any(b <= a for a, b in zip(s, s[1:])):
                raise ValueError("schedule_steps must be increasing step numbers from 1")
        return self


class Protocol(BaseModel):
    subject: Subject
    blocks: list[Block] = Field(min_length=1)
    plates: dict[str, str] | None = Field(None, description='{"left": plate, "right": plate}; default from the names')


def default_plates(plates: list[str]) -> dict[str, str]:
    """Plates named left / right, else the first plate = left (which index is the left belt: TODO)."""
    named = {s: p for s in SIDES for p in plates if s in p.lower()}
    if len(named) == 2 and named["left"] != named["right"]:
        return named
    if len(plates) < 2:
        raise ValueError(f"need two plates (one per belt), Vicon has {plates}")
    return {"left": plates[0], "right": plates[1]}


class Study:
    def __init__(self, protocol: Protocol, plates: list[str], send: Callable[[dict], int],
                 publish: Callable[[dict], None], log: Callable[[str, dict], None], rng: random.Random | None = None,
                 to_pc: Callable[[float], float | None] | None = None, now: Callable[[], float] | None = None,
                 report: Callable[[str, str], None] | None = None):
        """to_pc / now: plate clock → station-PC clock and the PC clock now (clocksync, D49): the touch-down's age is
        then measured on the PC clock; without them, from the frame it arrived in."""
        self.p, self._send, self._publish, self._log = protocol, send, publish, log
        self._to_pc, self._now = to_pc, now
        self._report = report or (lambda level, msg: None)   # (level, message) → the server's error log (D51)
        self.plates = protocol.plates or default_plates(plates)
        if set(self.plates) != set(SIDES) or any(p not in plates for p in self.plates.values()):
            raise ValueError(f"plates must map left and right to Vicon plates {plates}")
        self.rng = rng or random.Random()
        self._lock = threading.RLock()
        self.state, self.message = "loaded", None
        self.block_i, self.done, self.steps, self.since, self.target = 0, 0, 0, 0, 0
        self.seq: list[float] = []
        self.gaps: list[int] | None = None         # pattern gap per perturbation (steps), None = random / predefined
        self.t_start = 0.0                         # block (re)start, plate clock
        self.gait: dict[str, Any] | None = None
        self._rec: dict[str, tuple[list[float], list[float]]] | None = None   # gait pattern: (t, Fz) per side
        self._gait_until, self._gait_prev, self._gait_speed, self._gait_t0 = 0.0, "loaded", 0.0, 0.0
        self._t = 0.0                              # latest plate time (Vicon frame clock)
        self.latency_ms = 0.0                      # plates → board → rope, subtracted from the delay
        self._det = {s: ContactDetector() for s in SIDES}   # 100 / 25 N until a gait pattern sets the plate's own
        self._run = RunningDetector.for_mass(protocol.subject.mass_kg) if protocol.subject.mode == "running" else None
        for k, b in enumerate(protocol.blocks, 1):
            if b.pattern_items is not None and len(b.pattern_items) < b.n_perturbations:
                raise ValueError(f"block {k}: pattern {b.pattern} has {len(b.pattern_items)} perturbations, "
                                 f"the block wants {b.n_perturbations}")
        self._log("STUDY", {"load": self.p.subject.model_dump(), "blocks": len(self.p.blocks), "plates": self.plates})

    # --- status ---
    @property
    def block(self) -> Block:
        return self.p.blocks[self.block_i]

    def protocol(self) -> dict[str, Any]:
        return {**self.p.model_dump(), "plates": self.plates}

    def amplitude_n(self, b: Block | None = None) -> float:
        b = b or self.block
        if b.amplitude_mode == "newton":
            return round(b.amplitude, 2)
        pct = b.amplitude if b.amplitude_mode == "percent_bw" else b.intensity_pct_bw
        return round(pct / 100 * self.p.subject.mass_kg * G, 2)

    def status(self) -> dict[str, Any]:
        with self._lock:
            b = self.block
            nxt = None
            if self.state == "running" and self.done < b.n_perturbations:
                nxt = max(0, b.schedule_steps[self.done] - self.steps if self._predefined(b) else self.target - self.since)
            ends = None
            if self.state == "running" and b.duration_s:
                ends = round(max(0.0, b.duration_s - (self._t - self.t_start)))
            gait = None
            if self.gait or self._rec is not None:
                gait = {**(self.gait or {}), "until_s": round(max(0.0, self._gait_until - self._t), 1) if self.state == "gait" else None}
            return {"state": self.state, "message": self.message, "subject_id": self.p.subject.subject_id,
                    "block": self.block_i + 1, "blocks": len(self.p.blocks), "label": b.label, "speed_ms": b.speed_ms,
                    "amplitude_n": self.amplitude_n(), "done": self.done, "total": b.n_perturbations, "steps": self.steps,
                    "next_in_steps": nxt, "ends_in_s": ends, "latency_ms": self.latency_ms, "gait": gait, "plates": self.plates,
                    **self._next()}

    def _next(self) -> dict[str, Any]:
        i = self._next_index()
        speed = self.p.blocks[i].speed_ms
        return {"next_block": i + 1, "next_speed_ms": speed,
                "gait_ok": bool(self.gait) and abs(self.gait["speed_ms"] - speed) < 1e-6}

    def _changed(self) -> None:
        self._publish({"type": "study", **self.status()})

    # --- commands (HTTP threads) ---
    def record_gait(self, duration_s: float) -> None:
        with self._lock:
            if self.state in ("running", "gait"):
                raise RuntimeError(f"study is {self.state}")
            self._gait_prev, self.state, self.message = self.state, "gait", None
            self._rec, self._gait_t0, self._gait_until = {s: ([], []) for s in SIDES}, self._t, self._t + duration_s
            self._gait_speed = self.p.blocks[self._next_index()].speed_ms
        self._changed()

    def _next_index(self) -> int:
        """The block Start would run."""
        if self.state == "block_done" or (self.state == "gait" and self._gait_prev == "block_done"):
            return min(self.block_i + 1, len(self.p.blocks) - 1)
        return self.block_i

    def check_start(self) -> int:
        """Block index Start would run; RuntimeError with the reason when it cannot."""
        with self._lock:
            if self.state in ("running", "gait", "finished"):
                raise RuntimeError(f"study is {self.state}")
            n = self._next()
            if not n["gait_ok"]:
                raise RuntimeError(f"record the gait pattern at {n['next_speed_ms']:g} m/s first (block {n['next_block']})")
            i = n["next_block"] - 1
            msg = self.fit_check(i, resume=self.state == "stopped" and i == self.block_i)
            if msg:
                raise RuntimeError(msg)
            return i

    @staticmethod
    def _predefined(b: Block) -> bool:
        return not b.pattern_items and b.timing_mode == "predefined"

    def _gap_list(self, b: Block) -> list[int]:
        """Steps each perturbation needs after the previous (worst case for random)."""
        n = b.n_perturbations
        if b.pattern_items:
            return [int(it["gap_steps"]) for it in b.pattern_items[:n]]
        if b.timing_mode == "random":
            return [b.interval_max_steps] * n
        s = b.schedule_steps
        return [s[0]] + [y - x for x, y in zip(s, s[1:])]

    def fit_check(self, i: int, resume: bool = False) -> str | None:
        """None when block i's perturbations fit in its duration at the measured cadence (both feet, steps/s), else the
        reason with the maximum that fits (D50). A trigger foot other than "any" can cost one more step each."""
        b = self.p.blocks[i]
        if not b.duration_s or not self.gait:
            return None
        cad = 2000 / statistics.fmean([self.gait[s]["stride_ms"] for s in SIDES])     # steps per second
        gaps = self._gap_list(b)[self.done if resume else 0:]
        extra = 0 if b.trigger_side == "any" else 1
        t, k = b.warmup_s, 0
        for g in gaps:
            t += (g + extra) / cad
            if t > b.duration_s:
                break
            k += 1
        if k == len(gaps):
            return None
        need = b.warmup_s + sum(g + extra for g in gaps) / cad
        return (f"block {i + 1}: {len(gaps)} perturbations need about {need:.0f} s at {cad * 60:.0f} steps/min (measured), "
                f"the block is {b.duration_s:g} s: at most {k} fit. Make the block longer or use fewer perturbations "
                "in BumpemSetUp")

    def start(self, latency_ms: float = 0.0) -> None:
        with self._lock:
            i = self.check_start()
            self.latency_ms = latency_ms
            resume = self.state == "stopped" and i == self.block_i and self.seq
            if not resume:
                b = self.p.blocks[i]
                self.block_i, self.done, self.steps = i, 0, 0
                if b.pattern_items:                # same for every participant (D50)
                    items = b.pattern_items[:b.n_perturbations]
                    self.seq, self.gaps = [float(it["angle_deg"]) for it in items], [int(it["gap_steps"]) for it in items]
                else:
                    self.gaps = None
                    self.seq = [b.directions_deg[k % len(b.directions_deg)] for k in range(b.n_perturbations)]
                    if len(set(b.directions_deg)) > 1:
                        self.rng.shuffle(self.seq)
            self.since, self.t_start, self.state, self.message = 0, self._t, "running", None
            self._new_target()
            self._log("STUDY", {"start": self.block_i + 1, "resume": bool(resume), "label": self.block.label,
                                "amplitude_n": self.amplitude_n(), "latency_ms": latency_ms, "pattern": self.block.pattern,
                                "sequence": self.seq[self.done:], "gaps": self.gaps[self.done:] if self.gaps else None})
        self._changed()

    def stop(self, reason: str = "stopped by the operator") -> None:
        with self._lock:
            if self.state == "gait":
                self.state, self._rec = self._gait_prev, None
            elif self.state != "running":
                return
            else:
                self.state = "stopped"
            self.message = reason
            self._log("STUDY", {"stop": self.block_i + 1, "done": self.done, "reason": reason})
            if reason != "stopped by the operator":
                self._report("warn", f"block {self.block_i + 1} stopped: {reason}")
        self._changed()

    def _new_target(self) -> None:
        b = self.block
        if self.gaps:
            self.target = self.gaps[self.done] if self.done < len(self.gaps) else 0
        elif b.timing_mode == "random":
            self.target = self.rng.randint(b.interval_min_steps, b.interval_max_steps)

    # --- plate samples (Vicon thread) ---
    def on_samples(self, samples: list[tuple[float, dict[str, float]]], host_s: float | None = None) -> None:
        """One Vicon frame: (t_s on the frame clock, {plate: Fz}) per subsample, in order. `host_s`: server clock when
        the frame arrived (= its last subsample), for the stream's gait ticks."""
        if not samples:
            return
        t_end = samples[-1][0]
        if t_end < self._t - 0.5:                  # frame numbers restarted (Vicon reconnected)
            self._det = {s: ContactDetector(d.td_n, d.fo_n) for s, d in self._det.items()}
            if self._run is not None:
                self._run = self._run.reset()
            if self.state == "gait":
                self.stop("Vicon restarted during the gait pattern: record it again")
        off = (host_s - t_end) if host_s is not None else 0.0
        for t, fz in samples:
            self._t = t
            if self._run is not None:                       # running: both belts summed (D57)
                v = [fz.get(self.plates[side]) for side in SIDES]
                if None not in v:
                    rec = self._rec
                    if rec is not None:
                        for side, x in zip(SIDES, v):
                            rec[side][0].append(t)
                            rec[side][1].append(x)
                    for e, side, te in self._run.update(t, *v):
                        self._contact(side, e, te, t_end, te + off)
                if self.state == "gait" and t >= self._gait_until:
                    self._gait_done()
                continue
            for side in SIDES:
                v = fz.get(self.plates[side])
                if v is None:
                    continue
                rec = self._rec
                if rec is not None:
                    rec[side][0].append(t)
                    rec[side][1].append(v)
                e = self._det[side].update(t, v)
                if e:
                    self._contact(side, e, t, t_end, t + off)
            if self.state == "gait" and t >= self._gait_until:
                self._gait_done()

    def _contact(self, side: str, kind: str, t: float, t_end: float, host_t: float) -> None:
        with self._lock:
            if kind == FO:
                if self.state == "running":
                    self._log("FO", {"side": side})
                return
            b = self.block
            if self.state != "running" or t - self.t_start < b.warmup_s:    # warm-up: steps not counted
                self._publish({"type": "gait", "t_s": round(host_t, 4), "event": "FS", "side": side, "step": None})
                return
            if b.duration_s and t - self.t_start >= b.duration_s:          # time up before all were done
                self.state = "finished" if self.block_i == len(self.p.blocks) - 1 else "block_done"
                self.message = f"block duration {b.duration_s:g} s reached: {self.done} of {b.n_perturbations} perturbations"
                self._log("STUDY", {"done": self.block_i + 1, "reason": self.message})
                self._report("warn", f"block {self.block_i + 1}: {self.message}")
                self._changed()
                return
            self.steps += 1
            self.since += 1
            self._publish({"type": "gait", "t_s": round(host_t, 4), "event": "FS", "side": side, "step": self.steps})
            self._log("FS", {"side": side, "step": self.steps})
            due = self.steps >= b.schedule_steps[self.done] if self._predefined(b) else self.since >= self.target
            if not due or b.trigger_side not in ("any", side):
                return
            g = self.gait[side]
            phase = b.gait_phase_pct / 100 * (g["stance_ms"] if b.gait_phase_of == "stance" else g["stride_ms"])
            pc = self._to_pc(t) if self._to_pc else None
            age = (self._now() - pc) * 1000 if pc is not None and self._now else (t_end - t) * 1000
            delay, nxt = phase - age - self.latency_ms, 0
            while delay < 0:                       # too late for this contact: same phase of the side's next one (SLAP)
                delay, nxt = delay + g["stride_ms"], nxt + 1
            pert = {"angle_deg": self.seq[self.done], "amplitude_n": self.amplitude_n(), "phase1_ms": b.phase1_ms,
                    "dur_ms": b.dur_ms, "phase2_ms": b.phase2_ms, "delay_ms": round(delay, 1)}
            try:
                pid = self._send(pert)
            except Exception as e:                 # refused by the board / geometry: stop the block, say why
                self.state, self.message = "stopped", f"perturbation refused: {getattr(e, 'message', None) or e}"
                self._log("STUDY", {"stop": self.block_i + 1, "done": self.done, "reason": self.message})
                self._report("error", f"block {self.block_i + 1}: {self.message}")
                self._changed()
                return
            self.done += 1
            self._log("PERT", {"pulse_id": pid, "block": self.block_i + 1, "index": self.done, "side": side,
                               "step": self.steps, "next_contact": nxt, "td_pc": None if pc is None else round(pc, 4),
                               "phase_ms": round(phase, 1), "age_ms": round(age, 1), "latency_ms": self.latency_ms, **pert})
            self.since = 0
            self._new_target()
            if self.done >= b.n_perturbations:
                self.message = None
                self.state = "finished" if self.block_i == len(self.p.blocks) - 1 else "block_done"
                self._log("STUDY", {"done": self.block_i + 1})
        self._changed()

    def _gait_done(self) -> None:
        """Thresholds from each plate's swing noise (gait.fit_thresholds; running: the belt sum's, D57), then stride (TD → TD, 0.5–1.5 × median as
        the SLAP script) and stance (TD → FO) per side."""
        with self._lock:
            rec, self._rec = self._rec, None
            if rec is None:
                return
            n = sum(len(rec[s][0]) for s in SIDES) / 2
            res: dict[str, Any] = {"speed_ms": self._gait_speed, "rate_hz": round(n / max(1e-9, self._t - self._gait_t0)),
                                   "detector": "plates" if self._run is None else "sum"}
            if self._run is None:
                fits = {side: fit_thresholds(*rec[side]) for side in SIDES}
            else:
                ev = running_contacts(rec["left"][0], rec["left"][1], rec["right"][1], self._run.td_n, self._run.fo_n)
                fits = {side: {"events": [(k, t) for k, s, t in ev if s == side], "td_n": self._run.td_n,
                               "fo_n": self._run.fo_n, "noise_sd_n": None, "stable": True} for side in SIDES}
            short, unstable = [], []
            for side in SIDES:
                f = fits[side]
                tds = [t for k, t in f["events"] if k == TD]
                d = [b - a for a, b in zip(tds, tds[1:])]
                if d:
                    m = statistics.median(d)
                    d = [x for x in d if 0.5 * m <= x <= 1.5 * m]       # missed or extra touch-downs left out
                st = [b[1] - a[1] for a, b in zip(f["events"], f["events"][1:]) if a[0] == TD and b[0] == FO]
                if len(d) < MIN_STRIDES or len(st) < MIN_STRIDES:
                    short.append(f"{side} {min(len(d), len(st))}")
                    continue
                if not f["stable"]:
                    unstable.append(side)
                res[side] = {"stride_ms": round(statistics.mean(d) * 1000, 1), "sd_ms": round(statistics.pstdev(d) * 1000, 1),
                             "n": len(d), "stance_ms": round(statistics.mean(st) * 1000, 1),
                             "stance_sd_ms": round(statistics.pstdev(st) * 1000, 1),
                             "td_n": f["td_n"], "fo_n": f["fo_n"], "noise_sd_n": f["noise_sd_n"]}
            if short:
                self.state = self._gait_prev
                self.message = (f"gait pattern: too few strides ({', '.join(short)}; need {MIN_STRIDES} per side). "
                                "Subject on both belts, Vicon plates right?")
                self._report("warn", self.message)
            else:
                for side in SIDES:                 # the plate's own thresholds from now on (walking)
                    if self._run is None:
                        self._det[side] = ContactDetector(res[side]["td_n"], res[side]["fo_n"])
                self.gait = res
                notes = [f"low thresholds unstable on {', '.join(unstable)} (extra or missed touch-downs): "
                         "100 / 25 N kept there"] if unstable else []
                mode = self.p.subject.mode
                lim = MODE_LIMITS[mode]
                for side in SIDES:
                    st, ct = res[side]["stride_ms"] / 1000, res[side]["stance_ms"] / 1000
                    if not (lim["stride"][0] <= st <= lim["stride"][1] and lim["contact"][0] <= ct <= lim["contact"][1]):
                        notes.append(f"{side}: stride {st:.2f} s, contact {ct:.2f} s does not look like {mode} "
                                     f"(stride {lim['stride'][0]}–{lim['stride'][1]} s, contact {lim['contact'][0]}–"
                                     f"{lim['contact'][1]} s): mode, speed or plates right?")
                self.message = "; ".join(notes) or None
                if notes:
                    self._report("warn", "gait pattern: " + self.message)
                self.state = "ready" if self._gait_prev in ("loaded", "ready") else self._gait_prev
                self._log("STUDY", {"gait": res})
        self._changed()

    def vicon_lost(self) -> None:
        self.stop("Vicon lost")

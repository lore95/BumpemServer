"""Study runner (docs/API.md "Study", DECISIONS D44): one subject + blocks, foot strikes per belt from the Vicon
plates, each perturbation at a gait phase after a foot strike of the trigger side.

Pure logic: the server feeds plate samples (`on_samples`) and gives it `send` (one perturbation → pulse id),
`publish` (stream item) and `log` (events-file row). Thread-safe: samples come from the Vicon thread, commands from
HTTP requests.
"""
from __future__ import annotations

import random
import statistics
import threading
from typing import Any, Callable, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .gait import FS_VALID, GaitDetector

G = 9.81
MIN_STRIDES = 5          # per side, for a gait pattern
SIDES = ("left", "right")


class Subject(BaseModel):
    model_config = ConfigDict(extra="allow")
    subject_id: str = ""
    mass_kg: float = Field(gt=0, le=300)


class Block(BaseModel):
    model_config = ConfigDict(extra="allow")
    label: str = ""
    speed_ms: float = Field(gt=0, le=10)
    warmup_s: float = Field(0, ge=0, le=3600)
    n_perturbations: int = Field(ge=1, le=500)
    directions_deg: list[float] = Field(min_length=1)
    intensity_pct_bw: float = Field(gt=0, le=100)
    phase1_ms: float = Field(ge=0)
    dur_ms: float = Field(gt=0)
    phase2_ms: float = Field(ge=0)
    trigger_side: Literal["left", "right", "any"]
    gait_phase_pct: float = Field(ge=0, lt=100)
    timing_mode: Literal["random", "predefined"]
    interval_min_steps: int | None = Field(None, ge=1, le=1000)
    interval_max_steps: int | None = Field(None, ge=1, le=1000)
    schedule_steps: list[int] | None = None

    @model_validator(mode="after")
    def _timing(self):
        if self.phase1_ms + self.phase2_ms > self.dur_ms:
            raise ValueError("phase1_ms + phase2_ms longer than dur_ms")
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
                 publish: Callable[[dict], None], log: Callable[[str, dict], None], rng: random.Random | None = None):
        self.p, self._send, self._publish, self._log = protocol, send, publish, log
        self.plates = protocol.plates or default_plates(plates)
        if set(self.plates) != set(SIDES) or any(p not in plates for p in self.plates.values()):
            raise ValueError(f"plates must map left and right to Vicon plates {plates}")
        self.rng = rng or random.Random()
        self._lock = threading.RLock()
        self.state, self.message = "loaded", None
        self.block_i, self.done, self.steps, self.since, self.target = 0, 0, 0, 0, 0
        self.seq: list[float] = []
        self.t_start = 0.0                         # block (re)start, plate clock
        self.gait: dict[str, Any] | None = None
        self._gait_fs: dict[str, list[float]] | None = None
        self._gait_until, self._gait_prev, self._gait_speed = 0.0, "loaded", 0.0
        self._t = 0.0                              # latest plate time
        self._det = {s: GaitDetector() for s in SIDES}
        self._log("STUDY", {"load": self.p.subject.model_dump(), "blocks": len(self.p.blocks), "plates": self.plates})

    # --- status ---
    @property
    def block(self) -> Block:
        return self.p.blocks[self.block_i]

    def amplitude_n(self, b: Block | None = None) -> float:
        b = b or self.block
        return round(b.intensity_pct_bw / 100 * self.p.subject.mass_kg * G, 2)

    def status(self) -> dict[str, Any]:
        with self._lock:
            b = self.block
            nxt = None
            if self.state == "running" and self.done < b.n_perturbations:
                nxt = max(0, (self.target - self.since) if b.timing_mode == "random" else b.schedule_steps[self.done] - self.steps)
            gait = None
            if self.gait or self._gait_fs is not None:
                gait = {**(self.gait or {}), "until_s": round(max(0.0, self._gait_until - self._t), 1) if self.state == "gait" else None}
            return {"state": self.state, "message": self.message, "subject_id": self.p.subject.subject_id,
                    "block": self.block_i + 1, "blocks": len(self.p.blocks), "label": b.label, "speed_ms": b.speed_ms,
                    "amplitude_n": self.amplitude_n(), "done": self.done, "total": b.n_perturbations, "steps": self.steps,
                    "next_in_steps": nxt, "gait": gait, "plates": self.plates}

    def _changed(self) -> None:
        self._publish({"type": "study", **self.status()})

    # --- commands (HTTP threads) ---
    def record_gait(self, duration_s: float) -> None:
        with self._lock:
            if self.state in ("running", "gait"):
                raise RuntimeError(f"study is {self.state}")
            self._gait_prev, self.state, self.message = self.state, "gait", None
            self._gait_fs, self._gait_until = {s: [] for s in SIDES}, self._t + duration_s
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
            i = self._next_index()
            speed = self.p.blocks[i].speed_ms
            if not self.gait or abs(self.gait["speed_ms"] - speed) > 1e-6:
                raise RuntimeError(f"record the gait pattern at {speed:g} m/s first (block {i + 1})")
            return i

    def start(self) -> None:
        with self._lock:
            i = self.check_start()
            resume = self.state == "stopped" and i == self.block_i and self.seq
            if not resume:
                b = self.p.blocks[i]
                self.block_i, self.done, self.steps = i, 0, 0
                self.seq = [b.directions_deg[k % len(b.directions_deg)] for k in range(b.n_perturbations)]
                if len(set(b.directions_deg)) > 1:
                    self.rng.shuffle(self.seq)
            self.since, self.t_start, self.state, self.message = 0, self._t, "running", None
            self._new_target()
            self._log("STUDY", {"start": self.block_i + 1, "resume": bool(resume), "label": self.block.label,
                                "amplitude_n": self.amplitude_n(), "sequence": self.seq[self.done:]})
        self._changed()

    def stop(self, reason: str = "stopped by the operator") -> None:
        with self._lock:
            if self.state == "gait":
                self.state, self._gait_fs = self._gait_prev, None
            elif self.state != "running":
                return
            else:
                self.state = "stopped"
            self.message = reason
            self._log("STUDY", {"stop": self.block_i + 1, "done": self.done, "reason": reason})
        self._changed()

    def _new_target(self) -> None:
        b = self.block
        if b.timing_mode == "random":
            self.target = self.rng.randint(b.interval_min_steps, b.interval_max_steps)

    # --- plate samples (Vicon thread) ---
    def on_samples(self, samples: list[tuple[float, dict[str, float]]]) -> None:
        """(t_s, {plate: Fz}) per subsample, in order."""
        for t, fz in samples:
            self._t = t
            for side in SIDES:
                v = fz.get(self.plates[side])
                if v is not None and self._det[side].update(t, v) == FS_VALID:
                    self._foot_strike(side, t)
            if self.state == "gait" and t >= self._gait_until:
                self._gait_done()

    def _foot_strike(self, side: str, t: float) -> None:
        with self._lock:
            if self.state == "gait":
                self._gait_fs[side].append(t)
            if self.state != "running":
                self._publish({"type": "gait", "t_s": round(t, 4), "event": "FS", "side": side, "step": None})
                return
            self.steps += 1
            self.since += 1
            self._publish({"type": "gait", "t_s": round(t, 4), "event": "FS", "side": side, "step": self.steps})
            self._log("FS", {"side": side, "step": self.steps})
            b = self.block
            if t - self.t_start < b.warmup_s:
                return
            due = self.since >= self.target if b.timing_mode == "random" else self.steps >= b.schedule_steps[self.done]
            if not due or b.trigger_side not in ("any", side):
                return
            stride = self.gait[side]["stride_ms"]
            pert = {"angle_deg": self.seq[self.done], "amplitude_n": self.amplitude_n(), "phase1_ms": b.phase1_ms,
                    "dur_ms": b.dur_ms, "phase2_ms": b.phase2_ms, "delay_ms": round(b.gait_phase_pct / 100 * stride, 1)}
            try:
                pid = self._send(pert)
            except Exception as e:                 # refused by the board / geometry: stop the block, say why
                self.state, self.message = "stopped", f"perturbation refused: {getattr(e, 'message', None) or e}"
                self._log("STUDY", {"stop": self.block_i + 1, "done": self.done, "reason": self.message})
                self._changed()
                return
            self.done += 1
            self._log("PERT", {"pulse_id": pid, "block": self.block_i + 1, "index": self.done, "side": side,
                               "step": self.steps, **pert})
            self.since = 0
            self._new_target()
            if self.done >= b.n_perturbations:
                self.state = "finished" if self.block_i == len(self.p.blocks) - 1 else "block_done"
                self._log("STUDY", {"done": self.block_i + 1})
        self._changed()

    def _gait_done(self) -> None:
        with self._lock:
            fs, self._gait_fs = self._gait_fs, None
            res: dict[str, Any] = {"speed_ms": self._gait_speed}
            short = []
            for side in SIDES:
                d = [b - a for a, b in zip(fs[side], fs[side][1:])]
                if d:
                    m = statistics.median(d)
                    d = [x for x in d if 0.5 * m <= x <= 1.5 * m]       # missed or extra strikes left out
                if len(d) < MIN_STRIDES:
                    short.append(f"{side} {len(d)}")
                    continue
                res[side] = {"stride_ms": round(statistics.mean(d) * 1000, 1),
                             "sd_ms": round(statistics.pstdev(d) * 1000, 1), "n": len(d)}
            if short:
                self.state = self._gait_prev
                self.message = (f"gait pattern: too few strides ({', '.join(short)}; need {MIN_STRIDES} per side). "
                                "Subject on both belts, Vicon plates right?")
            else:
                self.gait, self.message = res, None
                self.state = "ready" if self._gait_prev in ("loaded", "ready") else self._gait_prev
                self._log("STUDY", {"gait": res})
        self._changed()

    def vicon_lost(self) -> None:
        self.stop("Vicon lost")

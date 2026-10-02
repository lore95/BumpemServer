"""Simulated board speaking protocol v1 (docs/PROTOCOL.md). Mirrors firmware/src/main.ino logic;
the plant is a first-order lag, not a motor model.

`SimLink(realtime=False)` advances virtual time on every readline, for fast tests."""
from __future__ import annotations

import collections
import random
import threading
import time

from .protocol import CHANNELS, F_HARD_MAX

DEFAULTS: dict[str, float] = {
    "loop_ms": 10, "kp_track": 0.24, "kd_track": 3.5, "kp_pulse": 0.24, "kd_pulse": 3.5,
    "kff": 7.5, "rc": 0.01905, "kt": 0.1524, "i_full": 30, "f_full": 200,
    "baseline_n": 5, "fmax_n": 200, "fault_n": 195, "fault_ms": 20,
    "filter_hz": 0, "d_window": 1, "arm_ms": 2000, "pulse_max_ms": 1000,
    "tel_div": 1, "wd_ms": 0,
    "ch_A": 1, "ch_B": 1, "ch_C": 1, "ch_D": 0,
    "gain_A": 1, "gain_B": 1, "gain_C": 1, "gain_D": 1,
    "offset_A": 0, "offset_B": 0, "offset_C": 0, "offset_D": 0,
}
RANGES: dict[str, tuple[float, float]] = {
    "loop_ms": (1, 50), "kff": (0, 20), "rc": (0.001, 0.2), "kt": (0.001, 10), "i_full": (1, 100),
    "f_full": (1, 1000), "baseline_n": (0, 30), "fmax_n": (0, F_HARD_MAX), "fault_n": (0, F_HARD_MAX),
    "fault_ms": (1, 1000), "filter_hz": (0, 500), "d_window": (1, 8), "arm_ms": (0, 10000),
    "pulse_max_ms": (1, 5000), "tel_div": (0, 1000), "wd_ms": (0, 60000),
    **{k: (0, 100) for k in ("kp_track", "kd_track", "kp_pulse", "kd_pulse")},
    **{f"ch_{c}": (0, 1) for c in CHANNELS}, **{f"gain_{c}": (0.5, 2) for c in CHANNELS},
    **{f"offset_{c}": (-20, 20) for c in CHANNELS},
}
DISARMED_ONLY = {"loop_ms", *(f"ch_{c}" for c in CHANNELS)}


class SimLink:
    def __init__(self, realtime: bool = True, lag_ms: float = 15.0, noise_n: float = 0.4, seed: int | None = None):
        self.realtime, self.lag_ms, self.noise_n = realtime, lag_ms, noise_n
        self._rng = random.Random(seed)
        self._lock = threading.Lock()
        self._out: collections.deque[str] = collections.deque()
        self._t0 = time.monotonic()
        self._vt = 0.0                      # virtual ms (realtime=False)
        self._next_tick = 0.0
        self.p = dict(DEFAULTS)
        self.state = "DISARMED"
        self.pulse: dict | None = None
        self.force = {c: 0.0 for c in CHANNELS}
        self.tgt = {c: 0.0 for c in CHANNELS}
        self.ramp = (0.0, 0.0, 0.0)          # t0, ms, from
        self.loops = 0
        self.last_rx = 0.0
        self.wd_tripped = False
        self._closed = False
        self._emit("I,proto=1,fw=sim,board=sim,channels=4,f_hard_max=200")
        self._event("STATE", "DISARMED")

    # ---------- time / output ----------
    def now(self) -> float:
        return (time.monotonic() - self._t0) * 1000 if self.realtime else self._vt

    def _emit(self, line: str) -> None:
        self._out.append(line)

    def _event(self, kind: str, *args) -> None:
        self._emit(",".join(["E", str(int(self.now())), kind, *map(str, args)]))

    def _set_state(self, s: str) -> None:
        if s != self.state:
            self.state = s
            self._event("STATE", s)

    # ---------- Link interface ----------
    def write(self, data: bytes) -> None:
        with self._lock:
            for line in data.decode("ascii").splitlines():
                self.last_rx, self.wd_tripped = self.now(), False
                self._handle(line)

    def readline(self) -> bytes:
        while not self._closed:
            with self._lock:
                if self._out:
                    return (self._out.popleft() + "\r\n").encode()
                now = self.now()
                if now >= self._next_tick:
                    self._tick(now)
                    self._next_tick = now + self.p["loop_ms"]
                    continue
                wait = self._next_tick - now
            if self.realtime:
                time.sleep(wait / 1000)
            else:
                with self._lock:
                    self._vt = self._next_tick
        return b""

    def close(self) -> None:
        self._closed = True

    # ---------- control ----------
    def _pulse_amp(self, c: str, now: float) -> float:
        pl = self.pulse
        if not pl:
            return 0.0
        if pl["phase"] == "ACTIVE":
            e, a = now - pl["start"], pl["amp"][c]
            if e < pl["rise"]:
                return a * e / pl["rise"]
            if e < pl["dur"] - pl["fall"]:
                return a
            if e < pl["dur"]:
                return a * (pl["dur"] - e) / pl["fall"]
            return 0.0
        if pl["phase"] == "ABORTING":
            e = now - pl["t_abort"]
            return 0.0 if pl["fall"] <= 0 or e >= pl["fall"] else pl["abort_level"][c] * (1 - e / pl["fall"])
        return 0.0

    def _abort(self, now: float) -> None:
        pl = self.pulse
        if not pl or pl["phase"] == "ABORTING":
            return
        if pl["phase"] == "ACTIVE":
            pl["abort_level"] = {c: self._pulse_amp(c, now) for c in CHANNELS}
            pl["t_abort"], pl["phase"] = now, "ABORTING"
        else:
            self.pulse = None
        self._event("PABORT", pl["id"])

    def _level(self, now: float) -> float:
        if self.state in ("ARMED", "FAULT"):
            return self.p["baseline_n"]
        if self.state in ("ARMING", "RELEASING"):
            t0, ms, frm = self.ramp
            to = self.p["baseline_n"] if self.state == "ARMING" else 0.0
            return to if ms <= 0 or now - t0 >= ms else frm + (to - frm) * (now - t0) / ms
        return 0.0

    def _tick(self, now: float) -> None:
        wd = self.p["wd_ms"]
        if wd > 0 and not self.wd_tripped and now - self.last_rx > wd:
            self.wd_tripped = True
            self._abort(now)
            self._event("WD")
        pl = self.pulse
        if pl and pl["phase"] == "PENDING" and now >= pl["start"]:
            pl["phase"] = "ACTIVE"
            self._event("PSTART", pl["id"])
        if pl and pl["phase"] == "ACTIVE" and now - pl["start"] >= pl["dur"]:
            self.pulse = None
            self._event("PEND", pl["id"])
        if pl and pl["phase"] == "ABORTING" and (pl["fall"] <= 0 or now - pl["t_abort"] >= pl["fall"]):
            self.pulse = None

        level = self._level(now)
        driving = self.state in ("ARMED", "FAULT", "ARMING", "RELEASING")
        a = self.p["loop_ms"] / (self.lag_ms + self.p["loop_ms"])
        dac = {}
        for c in CHANNELS:
            on = driving and self.p[f"ch_{c}"] >= 0.5
            self.tgt[c] = min(level + self._pulse_amp(c, now), self.p["fmax_n"]) if on else 0.0
            self.force[c] += a * (self.tgt[c] - self.force[c])
            ides = self.p["kff"] * self.tgt[c] * self.p["rc"] / self.p["kt"]
            dac[c] = int(min(max(ides / self.p["i_full"], 0.0), 1.0) * 4095) if on else 0

        if self.state == "ARMING" and now - self.ramp[0] >= self.ramp[1]:
            self._set_state("ARMED")
        if self.state == "RELEASING" and now - self.ramp[0] >= self.ramp[1]:
            self._set_state("DISARMED")

        self.loops += 1
        div = int(self.p["tel_div"])
        if div >= 1 and self.loops % div == 0:
            f = ["T", str(int(now)), self.state, str(self.pulse["id"] if self.pulse else 0)]
            for c in CHANNELS:
                meas = max(0.0, self.force[c] + self._rng.gauss(0, self.noise_n))
                f += [f"{self.tgt[c]:.2f}", f"{meas:.2f}", str(dac[c])]
            self._emit(",".join(f))

    # ---------- commands ----------
    def _ok(self, cmd: str, detail: str = "") -> None:
        self._emit(f"A,OK,{cmd}" + (f",{detail}" if detail else ""))

    def _err(self, cmd: str, why: str) -> None:
        self._emit(f"A,ERR,{cmd},{why}")

    def _handle(self, line: str) -> None:
        tok = line.split()
        if not tok:
            return
        cmd, now = tok[0].upper(), self.now()
        if cmd == "PING":
            self._ok(cmd)
        elif cmd == "INFO":
            self._emit("I,proto=1,fw=sim,board=sim,channels=4,f_hard_max=200")
            self._ok(cmd)
        elif cmd == "STATS":
            self._emit(f"I,loop_us_max=0,overruns=0,tx_drops=0,uptime_ms={int(now)}")
            self._ok(cmd)
        elif cmd == "GET":
            names = [n for n in self.p if len(tok) == 1 or n.lower() == tok[1].lower()]
            if not names:
                return self._err(cmd, "unknown parameter")
            for n in names:
                self._emit(f"P,{n},{self.p[n]:.5f}")
            self._ok(cmd)
        elif cmd == "SET":
            self._cmd_set(tok)
        elif cmd == "ARM":
            if self.state not in ("DISARMED", "ESTOP"):
                return self._err(cmd, "already armed")
            self.ramp = (now, self.p["arm_ms"], 0.0)
            self._set_state("ARMING")
            self._ok(cmd)
        elif cmd == "PULSE":
            self._cmd_pulse(tok, now)
        elif cmd == "ABORT":
            self._abort(now)
            self._ok(cmd)
        elif cmd == "RELEASE":
            try:
                ms = float(tok[1]) if len(tok) > 1 else 1000.0
            except ValueError:
                return self._err(cmd, "bad ms")
            if not 0 <= ms <= 10000:
                return self._err(cmd, "bad ms")
            if self.state not in ("ARMED", "FAULT"):
                return self._err(cmd, "not armed")
            self._abort(now)
            self.ramp = (now, ms, self.p["baseline_n"])
            self._set_state("RELEASING")
            self._ok(cmd)
        elif cmd in ("ESTOP", "STOP"):
            if self.pulse:
                self._abort(now)
            self.pulse = None
            self._set_state("ESTOP")
            self._ok("ESTOP")
        elif cmd == "CLEAR":
            if self.state != "FAULT":
                return self._err(cmd, "not in fault")
            self._set_state("ARMED")
            self._ok(cmd)
        else:
            self._err(cmd, "unknown command")

    def _cmd_set(self, tok: list[str]) -> None:
        if len(tok) != 3:
            return self._err("SET", "usage: SET name value")
        name = next((n for n in self.p if n.lower() == tok[1].lower()), None)
        if name is None:
            return self._err("SET", "unknown parameter")
        try:
            v = float(tok[2])
        except ValueError:
            return self._err("SET", "bad number")
        lo, hi = RANGES[name]
        if not lo <= v <= hi:
            return self._err("SET", "out of range")
        if self.pulse or self.state in ("ARMING", "RELEASING"):
            return self._err("SET", "busy")
        if name in DISARMED_ONLY and self.state not in ("DISARMED", "ESTOP"):
            return self._err("SET", "disarm first")
        if (name == "baseline_n" and v > self.p["fmax_n"]) or (name == "fmax_n" and v < self.p["baseline_n"]):
            return self._err("SET", "baseline_n > fmax_n")
        if name in ("loop_ms", "d_window", "tel_div"):
            v = round(v)
        self.p[name] = v
        self._ok("SET", name)

    def _cmd_pulse(self, tok: list[str], now: float) -> None:
        if len(tok) != 10:
            return self._err("PULSE", "usage: PULSE id delay rise dur fall aA aB aC aD")
        if self.state != "ARMED":
            return self._err("PULSE", "not armed")
        if self.pulse:
            return self._err("PULSE", "busy")
        try:
            v = [float(x) for x in tok[1:]]
        except ValueError:
            return self._err("PULSE", "bad number")
        pid, delay, rise, dur, fall = v[:5]
        amps = dict(zip(CHANNELS, v[5:]))
        if pid < 1:
            return self._err("PULSE", "id must be >= 1")
        if not 0 <= delay <= 10000:
            return self._err("PULSE", "delay out of range")
        if rise < 0 or fall < 0 or dur <= 0 or rise + fall > dur:
            return self._err("PULSE", "need rise+fall <= dur")
        if dur > self.p["pulse_max_ms"]:
            return self._err("PULSE", "dur > pulse_max_ms")
        for c, a in amps.items():
            if a < 0:
                return self._err("PULSE", "negative amplitude")
            if a > 0 and self.p[f"ch_{c}"] < 0.5:
                return self._err("PULSE", "channel disabled")
            if self.p["baseline_n"] + a > self.p["fmax_n"]:
                return self._err("PULSE", "exceeds fmax_n")
        self.pulse = {"id": int(pid), "phase": "PENDING", "start": now + delay,
                      "rise": rise, "dur": dur, "fall": fall, "amp": amps}
        self._ok("PULSE", str(int(pid)))

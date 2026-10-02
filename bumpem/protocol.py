"""Protocol v1. Mirrors docs/PROTOCOL.md — change both together."""
from __future__ import annotations

from dataclasses import dataclass

CHANNELS = ("A", "B", "C", "D")
ACTIVE_CHANNELS = ("A", "B", "C")  # D out of service (docs/knowledge/hardware.md)
F_HARD_MAX = 200.0
STATES = ("DISARMED", "ARMING", "ARMED", "FAULT", "RELEASING", "ESTOP")


# ---------- board -> host ----------
@dataclass(frozen=True)
class Telemetry:
    t_ms: int
    state: str
    pulse_id: int
    target: dict[str, float]
    measured: dict[str, float]
    dac: dict[str, int]


@dataclass(frozen=True)
class Ack:
    ok: bool
    cmd: str
    detail: str = ""


@dataclass(frozen=True)
class Event:
    t_ms: int
    kind: str
    args: tuple[str, ...] = ()


@dataclass(frozen=True)
class Info:
    fields: dict[str, str]


@dataclass(frozen=True)
class Param:
    name: str
    value: float


Message = Telemetry | Ack | Event | Info | Param | str


def parse_line(line: str) -> Message:
    """Parse one board line. Unrecognized lines are returned as stripped text."""
    line = line.strip()
    f = line.split(",")
    try:
        if f[0] == "T" and len(f) == 4 + 3 * len(CHANNELS):
            tgt, meas, dac = {}, {}, {}
            for i, ch in enumerate(CHANNELS):
                tgt[ch], meas[ch], dac[ch] = float(f[4 + 3 * i]), float(f[5 + 3 * i]), int(f[6 + 3 * i])
            return Telemetry(int(f[1]), f[2], int(f[3]), tgt, meas, dac)
        if f[0] == "A" and len(f) >= 3:
            return Ack(f[1] == "OK", f[2], ",".join(f[3:]))
        if f[0] == "E" and len(f) >= 3:
            return Event(int(f[1]), f[2], tuple(f[3:]))
        if f[0] == "I":
            return Info(dict(kv.split("=", 1) for kv in f[1:] if "=" in kv))
        if f[0] == "P" and len(f) == 3:
            return Param(f[1], float(f[2]))
    except ValueError:
        pass
    return line


# ---------- host -> board ----------
def encode(line: str) -> bytes:
    return (line.strip() + "\n").encode("ascii")


def _num(x: float) -> str:
    return f"{x:.6g}"


def set_cmd(name: str, value: float) -> str:
    return f"SET {name} {_num(value)}"


def pulse_cmd(pulse_id: int, amps: dict[str, float], *, delay_ms: float = 0, rise_ms: float,
              dur_ms: float, fall_ms: float) -> str:
    """Build a PULSE line. Amplitudes are relative to baseline (N). Host-side sanity checks only;
    the board re-validates against its own parameters."""
    if pulse_id < 1:
        raise ValueError("pulse_id must be >= 1")
    if not 0 <= delay_ms <= 10000:
        raise ValueError("delay_ms must be 0..10000")
    if rise_ms < 0 or fall_ms < 0 or dur_ms <= 0 or rise_ms + fall_ms > dur_ms:
        raise ValueError("need rise_ms + fall_ms <= dur_ms")
    unknown = set(amps) - set(CHANNELS)
    if unknown:
        raise ValueError(f"unknown channels {sorted(unknown)}")
    a = [float(amps.get(ch, 0.0)) for ch in CHANNELS]
    if any(x < 0 or x > F_HARD_MAX for x in a):
        raise ValueError(f"amplitudes must be 0..{F_HARD_MAX}")
    return " ".join(["PULSE", str(pulse_id)] + [_num(v) for v in (delay_ms, rise_ms, dur_ms, fall_ms, *a)])

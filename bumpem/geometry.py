"""Perturbation angle -> per-module amplitudes (docs/API.md "Perturbation form").

Vicon Forward/Left/Up axes seen from above: 0 = front, +90 = left, -90 = right, 180 = back.
The angle is the direction the subject is pulled; each module pulls towards where it stands.
Neighbouring modules are 90 deg apart; a pull between them is split as a vector
(legacy/Arduino_Script.ino:82: a 45 deg diagonal gives each cable force/sqrt(2)).
"""
from __future__ import annotations

import math

CONVENTION = "Vicon axes, seen from above: 0 = front, +90 = left, -90 = right, 180 = back"
MODULE_ANGLE_DEG = {"B": 0.0, "A": 90.0, "D": 180.0, "C": -90.0}   # docs/knowledge/hardware.md
_CCW = ["B", "A", "D", "C"]                                        # counter-clockwise from the front
_EPS = 1e-6


def normalize(angle_deg: float) -> float:
    """Map any angle to (-180, 180]."""
    a = math.fmod(angle_deg, 360.0)
    if a <= -180.0:
        a += 360.0
    elif a > 180.0:
        a -= 360.0
    return a


def split(angle_deg: float, amplitude_n: float, enabled: set[str] | None = None) -> dict[str, float]:
    """Amplitude above baseline per module for a pull of `amplitude_n` towards `angle_deg`.
    Raises ValueError if the angle needs a module that is not in `enabled` (None = all)."""
    if amplitude_n <= 0:
        raise ValueError("amplitude_n must be > 0")
    a = normalize(angle_deg) % 360.0                       # 0 <= a < 360, counter-clockwise from front
    i = int(a // 90.0) % 4
    delta = math.radians(a - 90.0 * i)                      # angle past module _CCW[i]
    first, second = _CCW[i], _CCW[(i + 1) % 4]
    amps = {first: amplitude_n * math.cos(delta), second: amplitude_n * math.sin(delta)}
    amps = {m: round(v, 2) for m, v in amps.items() if v > _EPS * amplitude_n and round(v, 2) > 0}
    missing = [m for m in amps if enabled is not None and m not in enabled]
    if missing:
        raise ValueError(f"angle {normalize(angle_deg):g} deg needs module {', '.join(missing)} "
                         f"({_where(missing)}), whose channel is off")
    return amps


def reachable(enabled: set[str]) -> list[dict[str, float]]:
    """Reachable directions as counter-clockwise arcs {from_deg, to_deg}; a single module gives from == to."""
    on = [m in enabled for m in _CCW]
    if all(on):
        return [{"from_deg": -180.0, "to_deg": 180.0}]
    arcs = []
    for j in range(4):
        if on[j] and not on[j - 1]:                         # a run of enabled modules starts at j
            k = j
            while on[(k + 1) % 4]:                          # ends: not all are on
                k = (k + 1) % 4
            arcs.append({"from_deg": MODULE_ANGLE_DEG[_CCW[j]], "to_deg": MODULE_ANGLE_DEG[_CCW[k]]})
    return arcs


def _where(mods: list[str]) -> str:
    names = {"A": "left", "B": "front", "C": "right", "D": "back"}
    return ", ".join(names[m] for m in mods)

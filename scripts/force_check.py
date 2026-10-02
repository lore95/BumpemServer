"""Force sensor check: 45 s of readings while you pull each rope by hand. The board stays DISARMED (no motor).

  python scripts/force_check.py                 # Teensy on the default port
  python scripts/force_check.py --port /dev/cu.usbmodemXXXX
  python scripts/force_check.py --sim           # try the script without hardware

Before: 48 V OFF. 24 V on. Each amplifier's output checked <= 3.3 V with the multimeter (docs/TODO.md step 2).
Brown force wires in the Teensy: A -> pin 14, C -> pin 16, D -> pin 17 (their short wires to the - rail removed).
Force = reading / 1023 * 200 N (firmware v1, docs/knowledge/calibration.md); no motor current is ever sent.
"""
from __future__ import annotations

import argparse
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bumpem import protocol as P  # noqa: E402
from bumpem.device import Board  # noqa: E402

MODS = ["A", "C", "D"]                       # mounted 2026-10-02: A left, C right, D back (B not installed)
PHASES = [  # (start s, end s, instruction, module that should rise)
    (0, 5, "hands off (zero)", None),
    (5, 13, "pull the LEFT rope (A)", "A"),
    (13, 18, "let go", None),
    (18, 26, "pull the RIGHT rope (C)", "C"),
    (26, 31, "let go", None),
    (31, 39, "pull the BACK rope (D)", "D"),
    (39, 45, "let go", None),
]
TOTAL_S = 45
RISE_N = 3.0                                  # a pull counts if the reading rises this much above the zero


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", default="/dev/cu.usbmodem169222501")
    ap.add_argument("--sim", action="store_true")
    a = ap.parse_args()

    if a.sim:
        from bumpem.sim import SimLink
        board = Board(SimLink())
    else:
        from bumpem.device import SerialLink
        board = Board(SerialLink(a.port))

    samples: list[tuple[float, dict[str, float]]] = []
    t0 = time.monotonic()

    def on_msg(msg: P.Message) -> None:
        if isinstance(msg, P.Telemetry):
            samples.append((time.monotonic() - t0, dict(msg.measured)))

    try:
        info = board.info()
        print(f"board: {info}")
        print("48 V must be OFF. The board is not armed by this script.\n")
        board.add_listener(on_msg)
        phase_i = -1
        while (t := time.monotonic() - t0) < TOTAL_S:
            i = next(k for k, ph in enumerate(PHASES) if ph[0] <= t < ph[1])
            if i != phase_i:
                phase_i = i
                print(f"\n>>> {PHASES[i][0]:>2}-{PHASES[i][1]} s: {PHASES[i][2].upper()}")
            if samples:
                m = samples[-1][1]
                print(f"  t={t:5.1f} s   " + "   ".join(f"{c} {m.get(c, float('nan')):6.1f} N" for c in MODS), end="\r")
            time.sleep(0.2)
        print()
    finally:
        board.close()

    if not samples:
        sys.exit("no telemetry received: is the Teensy running firmware v1 (bumpem info)?")
    report(samples)


def report(samples: list[tuple[float, dict[str, float]]]) -> None:
    def window(lo: float, hi: float, c: str) -> list[float]:
        return [m[c] for t, m in samples if lo <= t < hi and c in m]

    zero = {c: statistics.fmean(window(1, 5, c) or [0.0]) for c in MODS}
    print("\nzero (hands off, 1-5 s): " + "   ".join(f"{c} {zero[c]:.1f} N" for c in MODS))
    print("\nphase                       " + "".join(f"{c + ' peak rise':>14}" for c in MODS) + "   result")
    ok = True
    for lo, hi, what, expect in PHASES:
        if expect is None:
            continue
        rise = {c: max(window(lo, hi, c) or [zero[c]]) - zero[c] for c in MODS}
        risen = [c for c in MODS if rise[c] >= RISE_N]
        verdict = "OK" if risen == [expect] else (f"nothing rose (>= {RISE_N:g} N)" if not risen
                                                  else f"CHECK: {', '.join(risen)} rose, expected {expect}")
        ok &= verdict == "OK"
        print(f"{what:<28}" + "".join(f"{rise[c]:>12.1f} N" for c in MODS) + f"   {verdict}")
    noise = {c: statistics.pstdev(window(1, 5, c) or [0.0]) for c in MODS}
    print("\nnoise at rest (SD, 1-5 s): " + "   ".join(f"{c} {noise[c]:.2f} N" for c in MODS))
    print("\nALL OK: each pull moved only its own sensor." if ok else
          "\nNot all OK: note which line says CHECK / nothing rose and tell Claude.")


if __name__ == "__main__":
    main()

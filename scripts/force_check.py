"""Force sensor check, one module at a time: Enter -> 2 s zero -> pull that rope by hand -> Enter -> result.
The board stays DISARMED (no motor current is ever sent).

  python scripts/force_check.py                 # A, then C, then D
  python scripts/force_check.py --mods C D      # only some modules
  python scripts/force_check.py --port /dev/cu.usbmodemXXXX
  python scripts/force_check.py --sim           # try the script without hardware

Before: 48 V OFF. 24 V on. Each amplifier's output checked <= 3.3 V with the multimeter (docs/TODO.md step 2).
Brown force wires in the Teensy: A -> pin 14, C -> pin 16, D -> pin 17 (their short wires to the - rail removed).
Force = reading / 1023 * 200 N (firmware v1, docs/knowledge/calibration.md).
"""
from __future__ import annotations

import argparse
import statistics
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bumpem import protocol as P  # noqa: E402
from bumpem.device import Board  # noqa: E402

ROPE = {"A": "LEFT", "B": "FRONT", "C": "RIGHT", "D": "BACK"}
SHOWN = ["A", "C", "D"]          # mounted 2026-10-02 (B not installed)
ZERO_S = 2.0
RISE_N = 5.0                     # a pull counts if the smoothed reading rises this much above the zero
SMOOTH_S = 0.25                  # peak is taken on 0.25 s averages, so single noise spikes (~±1-1.5 N) don't count


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", default="/dev/cu.usbmodem169222501")
    ap.add_argument("--sim", action="store_true")
    ap.add_argument("--mods", nargs="+", default=SHOWN, choices=list(ROPE), help="modules to check, in order")
    a = ap.parse_args()

    if a.sim:
        from bumpem.sim import SimLink
        board = Board(SimLink())
    else:
        from bumpem.device import SerialLink
        board = Board(SerialLink(a.port))

    samples: list[tuple[float, dict[str, float]]] = []
    lock = threading.Lock()

    def on_msg(msg: P.Message) -> None:
        if isinstance(msg, P.Telemetry):
            with lock:
                samples.append((time.monotonic(), dict(msg.measured)))

    def latest() -> dict[str, float]:
        with lock:
            return samples[-1][1] if samples else {}

    def since(t0: float) -> list[dict[str, float]]:
        with lock:
            return [m for t, m in samples if t >= t0]

    def smoothed_peak(t0: float, c: str) -> float:
        """highest 0.25 s average of channel c since t0"""
        with lock:
            rows = [(t, m[c]) for t, m in samples if t >= t0 and c in m]
        bins: dict[int, list[float]] = {}
        for t, v in rows:
            bins.setdefault(int((t - t0) / SMOOTH_S), []).append(v)
        return max(statistics.fmean(v) for v in bins.values()) if bins else float("nan")

    results = {}
    try:
        print(f"board: {board.info()}")
        print("48 V must be OFF. This script never arms the board.")
        board.add_listener(on_msg)
        for mod in a.mods:
            input(f"\n=== Module {mod} ({ROPE[mod]} rope). Hands off, then press Enter ")
            t0 = time.monotonic()
            while time.monotonic() - t0 < ZERO_S or (not since(t0) and time.monotonic() - t0 < 5.0):
                show("zeroing, hands off", latest())
                time.sleep(0.1)
            zero_rows = since(t0)
            if not zero_rows:
                sys.exit("\nthe Teensy stopped sending data (reset or USB dropped?). Check `bumpem info`, "
                         "replug the USB if needed, then run this script again.")
            zero = {c: statistics.fmean(r[c] for r in zero_rows) for c in SHOWN}

            done = threading.Event()
            threading.Thread(target=lambda: (input(), done.set()), daemon=True).start()
            print(f"\nPULL the {ROPE[mod]} rope now, then let go and press Enter")
            t1 = time.monotonic()
            while not done.is_set():
                show("pulling", latest(), zero)
                time.sleep(0.1)
            rise = {c: smoothed_peak(t1, c) - zero[c] for c in SHOWN}
            results[mod] = (zero, rise)
            print_result(mod, zero, rise)
    finally:
        board.close()

    print("\n=== Summary")
    all_ok = True
    for mod, (zero, rise) in results.items():
        v = verdict(mod, rise)
        all_ok &= v == "OK"
        print(f"  {mod} ({ROPE[mod].lower():5s}): zero " + "  ".join(f"{c} {zero[c]:6.1f}" for c in SHOWN)
              + "  |  rise " + "  ".join(f"{c} {rise[c]:6.1f}" for c in SHOWN) + f"  N  -> {v}")
    print("\nALL OK: each pull moved only its own sensor." if all_ok else "\nNot all OK: paste this summary to Claude.")


def show(label: str, m: dict[str, float], zero: dict[str, float] | None = None) -> None:
    vals = "   ".join(f"{c} {m.get(c, float('nan')):6.1f} N" + (f" ({m.get(c, 0) - zero[c]:+5.1f})" if zero else "")
                      for c in SHOWN)
    print(f"  {label:<20} {vals}   ", end="\r", flush=True)


def verdict(mod: str, rise: dict[str, float]) -> str:
    risen = [c for c in SHOWN if rise[c] >= RISE_N]
    if risen == [mod]:
        return "OK"
    if not risen:
        return f"nothing rose (>= {RISE_N:g} N): check wire / 24 V / amplifier"
    return f"CHECK: {', '.join(risen)} rose, expected {mod}"


def print_result(mod: str, zero: dict[str, float], rise: dict[str, float]) -> None:
    print(f"\n  zero:  " + "   ".join(f"{c} {zero[c]:6.1f} N" for c in SHOWN))
    print(f"  rise:  " + "   ".join(f"{c} {rise[c]:+6.1f} N" for c in SHOWN))
    print(f"  -> {verdict(mod, rise)}")
    if 80 <= zero[mod] <= 120 and rise[mod] < RISE_N:
        print(f"  note: {mod} sits near half scale (~100 N = 1.65 V) and does not move: its Teensy pin is probably "
              f"not connected (wrong row / wire not seated)")


if __name__ == "__main__":
    main()

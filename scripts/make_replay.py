"""Cut a participant's force-plate recording into a replay (D54): `bumpem serve --vicon replay:<name>` plays it back.

    python scripts/make_replay.py <vicon_*.csv> <name> [--from S] [--to S]

--from / --to: seconds from the start of the recording (default: all). Pick a stretch of steady gait, e.g. the warm-up
before the first pull (pulls are in the events file: PSTART rows). Writes replays/<name>.csv with t_s (from the cut),
frame, sub and the Fz_ columns only: no names, clocks or board times. replays/ is not in git: participant data.
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

REPLAY_DIR = Path(__file__).resolve().parents[1] / "replays"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("vicon_csv", type=Path)
    ap.add_argument("name", help="replay name: letters, digits, . _ -")
    ap.add_argument("--from", dest="t_from", type=float, default=0.0, help="seconds from the recording start")
    ap.add_argument("--to", dest="t_to", type=float, default=None, help="seconds from the recording start")
    a = ap.parse_args(argv)
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", a.name) or a.name.startswith("."):
        ap.error("name: letters, digits, . _ - only")
    with a.vicon_csv.open(newline="") as f:
        rd = csv.DictReader(f)
        fz = [c for c in rd.fieldnames or [] if c.startswith("Fz_")]
        if len(fz) < 2:
            ap.error(f"{a.vicon_csv}: needs two Fz_ columns, has {fz}")
        rows = list(rd)
    t = [float(r["host_s"]) for r in rows]                  # arrival clock: always filled (pc_s may be empty early on)
    start = t[0]
    keep = [r for r, ti in zip(rows, t) if ti - start >= a.t_from and (a.t_to is None or ti - start <= a.t_to)]
    while keep and keep[0]["sub"] != "0":                   # whole frames only
        keep.pop(0)
    if len(keep) < 100:
        ap.error("fewer than 100 samples in that stretch")
    frames = sorted({int(r["frame"]) for r in keep})
    subs = max(int(r["sub"]) for r in keep) + 1
    rate = round((len(frames) - 1) / (float(keep[-1]["host_s"]) - float(keep[0]["host_s"])))   # frames/s, ≈ Vicon's rate
    REPLAY_DIR.mkdir(exist_ok=True)
    out = REPLAY_DIR / f"{a.name}.csv"
    f0 = frames[0]
    with out.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t_s", "frame", "sub"] + fz)
        for r in keep:
            k, s = int(r["frame"]) - f0, int(r["sub"])
            w.writerow([f"{k / rate + s / (rate * subs):.4f}", k + 1, s] + [r[c] for c in fz])
    print(f"{out}: {len(frames)} frames ({len(frames) / rate:.1f} s at {rate} frames/s × {subs}), plates "
          f"{', '.join(c[3:] for c in fz)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

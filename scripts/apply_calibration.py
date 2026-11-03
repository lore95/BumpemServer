"""Sensor gains from a weight calibration (BumpemUI calibrate.html CSV) into the saved settings (DECISIONS D42).

Per sensor: gain = slope of expected force (kg x g) over the raw reading (gain 1, offset 0), with intercept when two or
more different weights were hung (the tara then does not matter), else through the tara. Writes `gain_X` into
settings.json; an existing `offset_X` is scaled by new/old gain (a zero offset = -raw at rest x gain, so it stays a zero).
Gains outside the firmware's 0.5-3 are reported and not written. Old file kept as settings.json.bak. Report to
calibration_<stamp>_applied.txt next to the CSV. The server writes the file to the board at the next Connect.

  python scripts/apply_calibration.py [CSV] [--settings BumpemServer/settings.json] [--dry-run]
  (no CSV: the newest calibration_*.csv in --search folders)
"""
from __future__ import annotations

import argparse
import csv
import json
import shutil
from datetime import datetime
from pathlib import Path

GAIN_RANGE = (0.5, 3.0)            # firmware PARAMS gain_X limits (firmware/src/main.ino)
WORST_OK_N = 2.0                   # worst point error above this: flagged


def fit(points: list[dict]) -> dict:
    """points: rows of kind "point" for one sensor → gain, intercept, worst error (N)."""
    x = [float(p["raw_mean_n"]) for p in points]
    y = [float(p["expected_n"]) for p in points]
    masses = {float(p["mass_kg"]) for p in points}
    if len(masses) >= 2:
        mx, my = sum(x) / len(x), sum(y) / len(y)
        sxx = sum((a - mx) ** 2 for a in x)
        gain = sum((a - mx) * (b - my) for a, b in zip(x, y)) / sxx
        icpt = my - gain * mx
    else:
        net = [float(p["raw_mean_n"]) - float(p["tare_n"]) for p in points]
        gain = sum(y) / sum(net)
        icpt = -gain * float(points[0]["tare_n"])
    worst = max(abs(gain * a + icpt - b) for a, b in zip(x, y))
    return {"gain": gain, "intercept_n": icpt, "worst_n": worst, "points": len(points), "weights": sorted(masses)}


def results(rows: list[dict]) -> dict[str, dict]:
    out = {}
    for c in "ABCD":
        pts = [r for r in rows if r["sensor"] == c and r["kind"] == "point"]
        if pts:
            out[c] = fit(pts)
    return out


def apply(res: dict[str, dict], settings: Path, dry: bool) -> list[str]:
    saved = json.loads(settings.read_text()) if settings.is_file() else {"params": {}}
    params = dict(saved.get("params") or {})
    lines = []
    for c, r in res.items():
        g = round(r["gain"], 4)
        if not GAIN_RANGE[0] <= g <= GAIN_RANGE[1]:
            lines.append(f"{c}: gain {g} outside the firmware range {GAIN_RANGE[0]}-{GAIN_RANGE[1]}: NOT written "
                         "(amplifier trim or firmware range change needed)")
            continue
        old = float(params.get(f"gain_{c}", 1.0))
        params[f"gain_{c}"] = g
        msg = f"{c}: gain {old:g} -> {g:g}"
        if f"offset_{c}" in params and old > 0:
            o = round(float(params[f"offset_{c}"]) * g / old, 2)
            msg += f", offset {params[f'offset_{c}']:g} -> {o:g}"
            params[f"offset_{c}"] = o
        lines.append(msg)
    if not dry:
        if settings.is_file():
            shutil.copy2(settings, settings.with_suffix(".json.bak"))
        settings.parent.mkdir(parents=True, exist_ok=True)
        settings.write_text(json.dumps({"saved": datetime.now().isoformat(timespec="seconds"), "params": params}, indent=1))
    return lines


def newest(folders: list[Path]) -> Path | None:
    found = [p for d in folders if d.is_dir() for p in d.glob("calibration_*.csv")]
    return max(found, key=lambda p: p.stat().st_mtime) if found else None


def main() -> None:
    here = Path(__file__).resolve().parents[1]
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", nargs="?", help="calibration CSV (default: newest calibration_*.csv in --search)")
    ap.add_argument("--settings", default=str(here / "settings.json"))
    ap.add_argument("--search", nargs="*", default=[str(here.parent), str(Path.home() / "Downloads")])
    ap.add_argument("--dry-run", action="store_true", help="report only, settings unchanged")
    a = ap.parse_args()
    path = Path(a.csv) if a.csv else newest([Path(d) for d in a.search])
    if path is None or not path.is_file():
        raise SystemExit("No calibration_*.csv found: put it in the BumpemLab folder (or Downloads) and run again.")
    with path.open(newline="") as f:
        rows = list(csv.DictReader(f))
    res = results(rows)
    out = [f"Calibration {path.name} -> {a.settings}{' (dry run)' if a.dry_run else ''}", ""]
    if not res:
        raise SystemExit(f"{path.name}: no weight points in it.")
    for c, r in res.items():
        flag = []
        if len(r["weights"]) < 2:
            flag.append("one weight only")
        if r["worst_n"] > WORST_OK_N:
            flag.append(f"worst error > {WORST_OK_N} N: check the points")
        out.append(f"{c}: gain {r['gain']:.4f} from {r['points']} points, weights {r['weights']} kg, worst error "
                   f"{r['worst_n']:.2f} N{'  [' + '; '.join(flag) + ']' if flag else ''}")
    out.append("")
    out += apply(res, Path(a.settings), a.dry_run)
    out += ["", "Next: start_server.bat, Connect (the saved settings go to the board), Zero sensors with the ropes slack,",
            "Save as default."]
    text = "\n".join(out)
    print(text)
    if not a.dry_run:
        rep = path.with_name(path.stem + "_applied.txt")
        rep.write_text(text + "\n", encoding="utf-8")
        print(f"\nReport: {rep}")


if __name__ == "__main__":
    main()

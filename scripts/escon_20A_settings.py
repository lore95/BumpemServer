"""Saved settings for the ESCON 20 A range (escon/README.md, 2026-11-20): the drivers now give 20 A at the DAC's 3.3 V,
so the board needs `i_full` 20 and the control gains found on the Mac (A on target at 20 / 50 / 100 N), and
Max force 79 N (75 N pull + 4 N rest: the aluminium shafts slip above, D56).

Runs from update.bat after the PC's settings.json is put back. Changes only the keys in CONTROL, and only while the file
is still on the old range (`i_full` not 20, or no file: the board's firmware defaults are kff 7.5 / `i_full` 30, about 4x
too strong): a later tuning on that PC (with `i_full` 20) is kept. Sensor gains, offsets and the fault limit are kept.
Old file kept as settings.json.bak. The server writes the file to the board at the next Connect.

  python scripts/escon_20A_settings.py [--settings BumpemServer/settings.json] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path

CONTROL = {"i_full": 20.0, "kff": 0.9, "kp_track": 0.08, "kp_pulse": 0.08, "kd_track": 0.2, "kd_pulse": 0.2,
           "fmax_n": 79.0}          # max force: 75 N pull + 4 N rest until the steel shafts (docs/tower-limits.md, D56)


def apply(settings: Path, dry: bool) -> list[str]:
    saved = json.loads(settings.read_text()) if settings.is_file() else None
    params = dict((saved or {}).get("params") or {})
    if saved is not None and float(params.get("i_full", 30)) == CONTROL["i_full"]:
        return [f"{settings}: already on the 20 A range (i_full 20): nothing changed"]
    lines = [f"{settings}: " + ("no saved settings yet: new file with the 20 A control values" if saved is None
                                else "set to the 20 A range")]
    lines += [f"  {k}: {params.get(k, 'firmware default')} -> {v:g}" for k, v in CONTROL.items()]
    params.update(CONTROL)
    if not dry:
        if settings.is_file():
            shutil.copy2(settings, settings.with_suffix(".json.bak"))
        settings.parent.mkdir(parents=True, exist_ok=True)
        settings.write_text(json.dumps({"saved": datetime.now().isoformat(timespec="seconds"), "params": params}, indent=1))
    return lines


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--settings", type=Path, default=Path(__file__).resolve().parents[1] / "settings.json")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    for line in apply(a.settings, a.dry_run):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

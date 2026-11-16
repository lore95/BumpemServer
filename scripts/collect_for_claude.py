"""Everything Claude needs after a lab session in one zip (DECISIONS D51): error logs and delay reports of the last
30 days, the newest recordings (with a delay report each), VERSION.txt, settings.json, and the server's state if it
runs. Output: ForClaude_<stamp>.zip next to BumpemServer (the BumpemLab folder). Run by collect_for_claude.bat.

  python scripts/collect_for_claude.py [--recordings 3] [--logs BumpemServer/Logs]
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]                 # BumpemServer
sys.path.insert(0, str(HERE))
from bumpem.delays import analyze  # noqa: E402

DAYS = 30


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--recordings", type=int, default=3, help="newest recordings to include (default 3)")
    ap.add_argument("--logs", default=str(HERE / "Logs"))
    a = ap.parse_args()
    logs, root = Path(a.logs), HERE.parent
    out = root / f"ForClaude_{datetime.now().strftime('%Y%m%d_%H%M')}"
    out.mkdir()
    lines, cutoff = [], time.time() - DAYS * 86400
    for pattern in ("errors_*.jsonl", "delay_*.txt"):
        for f in sorted(logs.glob(pattern)) if logs.is_dir() else []:
            if f.stat().st_mtime >= cutoff:
                shutil.copy2(f, out)
                lines.append(f"{f.name}")
    events = sorted(logs.glob("events_*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)[:a.recordings] if logs.is_dir() else []
    for ev in events:
        force, vicon = ev.with_name(ev.name.replace("events_", "force_")), ev.with_name(ev.name.replace("events_", "vicon_"))
        for f in (ev, force, vicon):
            if f.is_file():
                shutil.copy2(f, out)
                lines.append(f.name)
        if force.is_file():
            try:
                rep = analyze(ev, force, vicon if vicon.is_file() else None)
                name = ev.name.replace("events_", "delay_").replace(".csv", ".txt")
                (out / name).write_text(rep["text"], encoding="utf-8")
                lines.append(f"{name} (made now)")
            except Exception as e:                          # a broken file must not stop the collection
                lines.append(f"delay report of {ev.name} failed: {e!r}")
    for f in (root / "VERSION.txt", HERE / "settings.json"):
        if f.is_file():
            shutil.copy2(f, out)
            lines.append(f.name)
    state = {}
    for path in ("info", "sync", "study", "errors?limit=50"):     # only if the server runs right now
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:8000/api/v1/{path}", timeout=2) as r:
                state[path] = json.load(r)
        except Exception as e:
            state[path] = f"not available ({e.__class__.__name__})"
    (out / "server_state.json").write_text(json.dumps(state, indent=1, default=str), encoding="utf-8")
    (out / "CONTENTS.txt").write_text("\n".join(["Collected " + datetime.now().isoformat(timespec="seconds"), ""] + lines) + "\n",
                                      encoding="utf-8")
    zip_path = shutil.make_archive(str(out), "zip", out)
    shutil.rmtree(out)
    print(f"{len(lines)} files collected into\n  {zip_path}\nCopy that .zip to the USB stick and give it to Claude.")


if __name__ == "__main__":
    main()

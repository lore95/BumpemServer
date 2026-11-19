"""Session zip (docs/API.md "Study" → Session zip, DECISIONS D53): every file of one loaded study in one zip,
named <subject_id>_<study_name>_<YYYY-MM-DD>_<HHMM>.zip in the log folder."""
from __future__ import annotations

import json
import re
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from .delays import analyze as analyze_delays


def zip_name(subject_id: str, study_name: str, t0: datetime) -> str:
    part = lambda s: re.sub(r"[^A-Za-z0-9_-]+", "-", s.strip()).strip("-")   # noqa: E731  (spaces → -)
    bits = [part(subject_id) or "subject", part(study_name), t0.strftime("%Y-%m-%d_%H%M")]
    return "_".join(b for b in bits if b)


def recording_files(folder: Path, stem: str) -> list[Path]:
    """The CSVs of one recording, plus its delay report (written now if missing and the recording has events + force)."""
    files = [folder / f"force_{stem}.csv", folder / f"events_{stem}.csv"] + sorted(folder.glob(f"vicon_{stem}*.csv"))
    files = [f for f in files if f.is_file()]
    delay = folder / f"delay_{stem}.txt"
    if not delay.is_file() and (folder / f"events_{stem}.csv").is_file() and (folder / f"force_{stem}.csv").is_file():
        vicon = next((f for f in files if f.name.startswith("vicon_")), None)
        try:
            delay.write_text(analyze_delays(folder / f"events_{stem}.csv", folder / f"force_{stem}.csv", vicon)["text"],
                             encoding="utf-8")
        except Exception as e:                     # a broken recording must not stop the export
            delay.write_text(f"Delay report failed: {e}\n", encoding="utf-8")
    return files + [delay] if delay.is_file() else files


def export(folder: str | Path, name: str, stems: list[str], extra: dict[str, Any], errors: list[Path]) -> dict[str, Any]:
    """Write <folder>/<name>.zip (or <name>_2.zip …): the recordings of `stems`, `extra` as JSON files, the error logs."""
    folder = Path(folder)
    out, n = folder / f"{name}.zip", 1
    while out.exists():
        n += 1
        out = folder / f"{name}_{n}.zip"
    root = out.stem
    listed = []
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for stem in stems:
            for f in recording_files(folder, stem):
                z.write(f, f"{root}/{f.name}")
                listed.append(f.name)
        for fname, data in extra.items():
            if data is not None:
                z.writestr(f"{root}/{fname}", json.dumps(data, indent=1, default=str))
                listed.append(fname)
        for f in errors:
            if f.is_file():
                z.write(f, f"{root}/{f.name}")
                listed.append(f.name)
    return {"file": str(out), "name": out.name, "files": listed, "recordings": len(stems)}


def _read(z: zipfile.ZipFile, fname: str) -> Any:
    hit = next((n for n in z.namelist() if n.endswith("/" + fname) or n == fname), None)
    return json.loads(z.read(hit)) if hit else None


def saved(folder: str | Path) -> list[dict[str, Any]]:
    """Session zips in the folder that hold a protocol.json, newest first."""
    out = []
    for f in sorted(Path(folder).glob("*.zip"), key=lambda f: f.stat().st_mtime, reverse=True):
        try:
            with zipfile.ZipFile(f) as z:
                p, st = _read(z, "protocol.json"), _read(z, "study.json") or {}
        except (zipfile.BadZipFile, OSError, ValueError):
            continue
        if not p or "subject" not in p:
            continue
        subj = p["subject"]
        out.append({"name": f.name, "subject_id": subj.get("subject_id", ""), "study_name": subj.get("study_name", ""),
                    "loaded": st.get("loaded"), "blocks": len(p.get("blocks", [])), "mode": subj.get("mode")})
    return out


def saved_protocol(folder: str | Path, name: str) -> dict[str, Any] | None:
    f = Path(folder) / name
    if Path(name).name != name or f.suffix != ".zip" or not f.is_file():   # only a zip in the log folder itself
        return None
    try:
        with zipfile.ZipFile(f) as z:
            return _read(z, "protocol.json")
    except (zipfile.BadZipFile, OSError, ValueError):
        return None

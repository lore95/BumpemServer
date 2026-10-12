"""CSV logs with the same headers as the MATLAB script (docs/knowledge/experiment.md)."""
from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

EVENT_HEADER = ["time_s", "frame", "subIndex", "Fz_total", "event"]
PERT_HEADER = ["perturbation_index", "fs_number", "time_s", "frame", "subIndex", "command"]
FORCE_HEADER = ["time_ms", "state", "pulse_id"] + [f"{k}_{c}" for c in "ABCD" for k in ("target", "measured", "dac")]  # protocol v1 telemetry


class TrialLog:
    def __init__(self, folder: str | Path = "Logs"):
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._files, self.w = {}, {}
        for name, header in (("event", EVENT_HEADER), ("pert", PERT_HEADER), ("force", FORCE_HEADER)):
            f = open(folder / f"{name}_{ts}.csv", "w", newline="")
            self._files[name] = f
            self.w[name] = csv.writer(f)
            self.w[name].writerow(header)

    def close(self):
        for f in self._files.values():
            f.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


class ForceLog:
    """Full-rate telemetry + events of one recording (server `POST /log/start`, docs/API.md "Recording")."""

    def __init__(self, folder: str | Path, label: str = ""):
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        stem = datetime.now().strftime("%Y%m%d_%H%M%S") + (f"_{label}" if label else "")
        self.force_path, self.events_path = folder / f"force_{stem}.csv", folder / f"events_{stem}.csv"
        self._ff, self._ef = open(self.force_path, "w", newline=""), open(self.events_path, "w", newline="")
        self._fw, self._ew = csv.writer(self._ff), csv.writer(self._ef)
        self._fw.writerow(FORCE_HEADER)
        self._ew.writerow(["time_ms", "kind", "args"])
        self.rows, self.t_first, self.t_last = 0, None, 0

    def telemetry(self, t) -> None:
        row = [t.t_ms, t.state, t.pulse_id]
        for c in "ABCD":
            row += [t.target[c], t.measured[c], t.dac[c]]
        self._fw.writerow(row)
        self.rows += 1
        self.t_first = t.t_ms if self.t_first is None else self.t_first
        self.t_last = t.t_ms

    def event(self, t_ms: int, kind: str, args: str) -> None:
        self._ew.writerow([t_ms, kind, args])

    @property
    def duration_s(self) -> float:
        return 0.0 if self.t_first is None else (self.t_last - self.t_first) / 1000

    def close(self) -> None:
        self._ff.close()
        self._ef.close()

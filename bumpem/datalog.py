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

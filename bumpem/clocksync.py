"""Device clock → station-PC clock (docs/API.md "Clocks and sync", DECISIONS D49).

Feed (device_s, pc_s) for every sample as it arrives. Arrival = true time + a transport delay ≥ its minimum, so per
`bin_s` of device time the pair with the smallest pc − device (the least-delayed arrival) is kept, and a least-squares
line through the last `window_s` of those gives pc_s = a + b · device_s: offset and drift (before 3 points: offset
only). Jitter = sd of the kept points around the line. A device clock that jumps back (restart, Vicon reconnect) starts a new fit.
"""
from __future__ import annotations

import math
import statistics
import threading
from collections import deque


class ClockFit:
    def __init__(self, window_s: float = 60.0, bin_s: float = 1.0):
        self.window_s, self.bin_s = window_s, bin_s
        self._lock = threading.Lock()         # fed by a reader thread, read by HTTP threads
        self.reset()

    def reset(self) -> None:
        with self._lock:
            self._reset()

    def _reset(self) -> None:
        self._pts: deque[tuple[float, float]] = deque()   # (device_s, pc_s) least-delayed arrival per bin
        self._bin: int | None = None
        self._best: tuple[float, float] | None = None
        self._late: deque[float] = deque(maxlen=1000)     # recent arrival − line, s
        self._line: tuple[float, float] | None = None     # a, b
        self.last_dev = self.last_pc = None

    def add(self, dev: float, pc: float) -> None:
        with self._lock:
            self._add(dev, pc)

    def _add(self, dev: float, pc: float) -> None:
        if self.last_dev is not None and dev < self.last_dev - 0.5:
            self._reset()
        self.last_dev, self.last_pc = dev, pc
        b = math.floor(dev / self.bin_s)
        if b != self._bin:
            if self._best is not None:
                self._pts.append(self._best)
                while self._pts and self._pts[-1][0] - self._pts[0][0] > self.window_s:
                    self._pts.popleft()
                self._refit()
            self._bin, self._best = b, (dev, pc)
        elif pc - dev < self._best[1] - self._best[0]:
            self._best = (dev, pc)
        if self._line is not None:
            self._late.append(pc - self._map(dev))

    def _refit(self) -> None:
        if len(self._pts) < 3:
            self._line = None
            return
        xs, ys = [p[0] for p in self._pts], [p[1] for p in self._pts]
        mx, my = statistics.fmean(xs), statistics.fmean(ys)
        sxx = sum((x - mx) ** 2 for x in xs)
        b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx if sxx > 0 else 1.0
        self._line = (my - b * mx, b)

    def to_pc(self, dev: float) -> float | None:
        with self._lock:
            return self._map(dev)

    def _map(self, dev: float) -> float | None:
        if self._line is None:                    # first seconds: offset only (least-delayed arrival so far)
            pts = list(self._pts) + ([self._best] if self._best else [])
            return dev + min(p - d for d, p in pts) if pts else None
        a, b = self._line
        return a + b * dev

    def status(self, now_pc: float) -> dict | None:
        with self._lock:
            return self._status(now_pc)

    def _status(self, now_pc: float) -> dict | None:
        if self._line is None:
            return None
        a, b = self._line
        res = [y - (a + b * x) for x, y in self._pts]
        late = sorted(self._late)
        return {"drift_ppm": round((b - 1) * 1e6, 1), "jitter_ms": round(statistics.pstdev(res) * 1000, 2),
                "late_ms": round(late[int(0.95 * (len(late) - 1))] * 1000, 2) if late else None,
                "span_s": round(self._pts[-1][0] - self._pts[0][0], 1),
                "age_ms": round((now_pc - self.last_pc) * 1000) if self.last_pc is not None else None}

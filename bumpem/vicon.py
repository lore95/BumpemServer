"""Vicon force plates over Ethernet (DataStream SDK): docs/API.md "Vicon force plates", DECISIONS D31.

Device data only (no markers). `start()` runs one reader thread; `on_frame(frame, subs)` gets each new frame with
`subs` = one {plate: Fz} dict per force-plate subsample, `on_end(message)` when the link is lost.
SDK: Vicon DataStream SDK 1.13 for Python (`vicon_dssdk`, shipped as a wheel, D36); calls checked against its
ViconDataStream.py. Force plate API as the legacy MATLAB script (GetForcePlates, GetGlobalForceVector): global
(lab) axes, force exerted on the plate (not the reaction), so standing reads negative Fz. Device data appear only
some frames after EnableDeviceData: wait for the plates. Connects to Nexus 2.8.1 (lab, 2026-11-02).
"""
from __future__ import annotations

import math
import random
import threading
import time
from typing import Callable

FrameFn = Callable[[int, list[dict[str, float]]], None]
EndFn = Callable[[str], None]


class ViconReader:
    """Nexus DataStream (`host` = "address:port", port 801)."""

    def __init__(self, host: str, on_frame: FrameFn, on_end: EndFn, timeout_s: float = 5.0):
        try:
            from vicon_dssdk import ViconDataStream
        except ImportError as e:   # not installed, or its DLLs do not load (Visual C++ runtime missing)
            raise ValueError(f"Vicon SDK not usable ({e}): run update.bat from a bundle that carries vicon_dssdk") from None
        self._V, self.host, self._on_frame, self._on_end = ViconDataStream, host, on_frame, on_end
        c = self._client = ViconDataStream.Client()
        try:
            c.Connect(host)
        except ViconDataStream.DataStreamException as e:
            raise ValueError(f"cannot connect to Vicon at {host} ({e}): Nexus open in Live mode? address right?") from None
        c.EnableDeviceData()
        try:                                            # every frame in order; ClientPull (legacy MATLAB) can skip frames
            c.SetStreamMode(ViconDataStream.Client.StreamMode.EServerPush)
        except Exception:
            pass
        end, frames, ids = time.monotonic() + timeout_s, 0, []
        while not ids:                                  # device data join the stream a few frames after enabling
            if time.monotonic() > end:
                c.Disconnect()
                if not frames:
                    raise TimeoutError(f"Vicon at {host}: connected but no frame within {timeout_s:.0f} s (Nexus in Live mode?)")
                raise ValueError(f"Vicon: {frames} frames but no force plate in the stream (force plates enabled in Nexus?)")
            if self._get_frame():
                frames += 1
                ids = list(c.GetForcePlates())
            else:
                time.sleep(0.01)
        self.rate_hz = float(c.GetFrameRate())
        self._ids = ids                                 # SDK plate IDs; names from the device list when they match
        names = [n for n, kind in c.GetDeviceNames() if getattr(kind, "name", str(kind)) == "EForceplate"]
        self.plates = names if len(names) == len(ids) and len(set(names)) == len(names) else [f"Plate {i}" for i in ids]
        self._stop = threading.Event()

    def start(self) -> None:
        threading.Thread(target=self._run, daemon=True).start()

    def _get_frame(self) -> bool:
        """True when a frame was fetched. The SDK returns False for NoFrame and raises for other errors."""
        try:
            return bool(self._client.GetFrame())
        except self._V.DataStreamException:
            return False

    def _run(self) -> None:
        last = None
        try:
            while not self._stop.is_set():
                if not self._get_frame():
                    if not self._client.IsConnected():
                        raise ConnectionError("Vicon connection lost")
                    time.sleep(0.001)
                    continue
                frame = int(self._client.GetFrameNumber())
                if frame == last:
                    time.sleep(0.0005)
                    continue
                last = frame
                cols = {p: self._client.GetGlobalForceVector(i) for p, i in zip(self.plates, self._ids)}
                n = min(len(v) for v in cols.values())
                self._on_frame(frame, [{p: float(v[k][2]) for p, v in cols.items()} for k in range(n)])
        except Exception as e:
            if not self._stop.is_set():
                self._on_end(str(e))

    def close(self) -> None:
        self._stop.set()
        try:
            self._client.Disconnect()
        except Exception:
            pass


class SimReader:
    """Two belts while running (host "sim"): 100 Hz frames of 10 subsamples, stride 0.72 s, stance 0.25 s, peak ~1500 N."""

    plates = ["Left", "Right"]

    def __init__(self, on_frame: FrameFn, on_end: EndFn, rate_hz: float = 100, subs: int = 10):
        self.host, self.rate_hz, self._subs, self._on_frame = "sim", rate_hz, subs, on_frame
        self._stop = threading.Event()

    def start(self) -> None:
        threading.Thread(target=self._run, daemon=True).start()

    @staticmethod
    def fz(t: float, offset: float) -> float:
        ph = ((t - offset) % 0.72) / 0.25
        return (1500 * math.sin(math.pi * ph) if ph < 1 else 0.0) + random.gauss(0, 4)

    def _run(self) -> None:
        t0, frame, dt = time.monotonic(), 0, 1 / self.rate_hz
        while not self._stop.wait(max(0.0, t0 + (frame + 1) * dt - time.monotonic())):
            frame += 1
            ts = [(frame - 1) * dt + (i + 1) * dt / self._subs for i in range(self._subs)]
            self._on_frame(frame, [{"Left": self.fz(t, 0), "Right": self.fz(t, 0.36)} for t in ts])

    def close(self) -> None:
        self._stop.set()


def open_reader(host: str, on_frame: FrameFn, on_end: EndFn):
    return SimReader(on_frame, on_end) if host == "sim" else ViconReader(host, on_frame, on_end)

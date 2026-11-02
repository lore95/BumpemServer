"""Vicon force plates over Ethernet (DataStream SDK): docs/API.md "Vicon force plates", DECISIONS D31.

Device data only (no markers). `start()` runs one reader thread; `on_frame(frame, subs)` gets each new frame with
`subs` = one {plate: Fz} dict per force-plate subsample, `on_end(message)` when the link is lost.
SDK: Vicon DataStream SDK 1.13 for Python (`vicon_dssdk`, shipped as a wheel, D36); calls checked against its
ViconDataStream.py. Force plate API as the legacy MATLAB script (GetForcePlates, GetGlobalForceVector): global
(lab) axes, force exerted on the plate (not the reaction), so Vicon's Fz reads negative when standing: the reader
negates it, so `subs` carry the vertical ground reaction force, positive up (D40). Device data appear only
some frames after EnableDeviceData: wait for the plates. Connects to Nexus 2.8.1 (lab, 2026-11-02).
"""
from __future__ import annotations

import importlib
import math
import multiprocessing
import random
import threading
import time
from typing import Callable

FrameFn = Callable[[int, list[dict[str, float]]], None]
EndFn = Callable[[str], None]


class ViconLost(Exception):
    """Nexus went away (not an OSError, so the worker can tell it from a closed pipe)."""


class _SdkSession:
    """The SDK connection itself, used inside the reader process (`_worker`). `sdk`: module holding ViconDataStream."""

    def __init__(self, host: str, timeout_s: float, sdk: str = "vicon_dssdk"):
        try:
            V = importlib.import_module(sdk).ViconDataStream
        except ImportError as e:   # not installed, or its DLLs do not load (Visual C++ runtime missing)
            raise ValueError(f"Vicon SDK not usable ({e}): run update.bat from a bundle that carries vicon_dssdk") from None
        self._V, self.host = V, host
        c = self._client = V.Client()
        try:
            c.Connect(host)
        except V.DataStreamException as e:
            raise ValueError(f"cannot connect to Vicon at {host} ({e}): Nexus open in Live mode? address right?") from None
        c.EnableDeviceData()
        try:                                            # every frame in order; ClientPull (legacy MATLAB) can skip frames
            c.SetStreamMode(V.Client.StreamMode.EServerPush)
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

    def _get_frame(self) -> bool:
        """True when a frame was fetched. The SDK returns False for NoFrame and raises for other errors."""
        try:
            return bool(self._client.GetFrame())
        except self._V.DataStreamException:
            return False

    def run(self, emit: FrameFn, stop: Callable[[], bool]) -> None:
        """Every new frame to `emit` until `stop()`; raises ViconLost when Nexus goes away."""
        last = None
        try:
            while not stop():
                if not self._get_frame():
                    if not self._client.IsConnected():
                        raise ViconLost("Vicon connection lost")
                    time.sleep(0.001)
                    continue
                frame = int(self._client.GetFrameNumber())
                if frame == last:
                    time.sleep(0.0005)
                    continue
                last = frame
                cols = {p: self._client.GetGlobalForceVector(i) for p, i in zip(self.plates, self._ids)}
                n = min(len(v) for v in cols.values())
                emit(frame, [{p: -float(v[k][2]) for p, v in cols.items()} for k in range(n)])   # GRF, up = +
        finally:
            try:
                self._client.Disconnect()
            except Exception:
                pass


def _worker(host: str, conn, timeout_s: float, sdk: str) -> None:
    """Reader process: ("ready", plates, rate) or ("error", kind, text), then ("frame", n, subs)…, ("end", text)."""
    try:
        s = _SdkSession(host, timeout_s, sdk)
    except Exception as e:
        conn.send(("error", "timeout" if isinstance(e, TimeoutError) else "invalid", str(e)))
        return
    conn.send(("ready", s.plates, s.rate_hz))
    try:
        s.run(lambda f, subs: conn.send(("frame", f, subs)), conn.poll)   # anything from the server = stop
        conn.send(("end", ""))
    except (BrokenPipeError, EOFError, OSError):
        pass                                                              # server gone
    except Exception as e:
        try:
            conn.send(("end", str(e)))
        except OSError:
            pass


class ViconReader:
    """Nexus DataStream (`host` = "address:port", port 801), read in a separate process.

    Vicon's compiled module never releases Python's GIL (no PyEval_SaveThread in _CoreClient3.pyd): its GetFrame waits
    for the next frame holding it, which froze the server's serial thread (board timeouts with Vicon connected,
    2026-11-02, D38). In its own process it can only block itself; frames come over a pipe.
    """

    def __init__(self, host: str, on_frame: FrameFn, on_end: EndFn, timeout_s: float = 5.0, sdk: str = "vicon_dssdk"):
        ctx = multiprocessing.get_context("spawn")      # Windows' only start method; same on the Mac for the tests
        self._conn, child = ctx.Pipe()
        self._proc = ctx.Process(target=_worker, args=(host, child, timeout_s, sdk), daemon=True, name="vicon")
        self._proc.start()
        child.close()
        self.host, self._on_frame, self._on_end = host, on_frame, on_end
        self._stop = threading.Event()
        try:
            msg = self._conn.recv() if self._conn.poll(timeout_s + 20) else ("error", "timeout", "Vicon reader did not start")
        except (EOFError, OSError):
            msg = ("error", "invalid", "Vicon reader process failed at start (see the server window)")
        if msg[0] != "ready":
            self.close()
            raise (TimeoutError if msg[1] == "timeout" else ValueError)(msg[2])
        _, self.plates, self.rate_hz = msg

    def start(self) -> None:
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self) -> None:
        text = "Vicon reader process ended"
        try:
            while not self._stop.is_set():
                msg = self._conn.recv()                 # blocks without holding the GIL
                if msg[0] == "frame":
                    self._on_frame(msg[1], msg[2])
                else:
                    text = msg[1] or text
                    break
        except (EOFError, OSError):
            pass
        if not self._stop.is_set():
            self._on_end(text)

    def close(self) -> None:
        self._stop.set()
        try:
            self._conn.send("stop")
        except OSError:
            pass
        self._proc.join(2)
        if self._proc.is_alive():
            self._proc.terminate()
        self._conn.close()


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

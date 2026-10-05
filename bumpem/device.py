"""Board client for protocol v1. Works over a real serial port or the simulator (`sim.SimLink`)."""
from __future__ import annotations

import queue
import threading
import time
from collections.abc import Callable, Iterator
from typing import Protocol

from . import protocol as P


class Link(Protocol):
    def write(self, data: bytes) -> None: ...
    def readline(self) -> bytes: ...   # returns b"" on timeout
    def close(self) -> None: ...


class SerialLink:
    """BUMPEM_SERIAL_LOG=<file>: append every command sent and every non-telemetry line received, with times."""

    def __init__(self, port: str, timeout: float = 0.1):
        import os
        import serial
        path = os.environ.get("BUMPEM_SERIAL_LOG")
        self._log = open(path, "a", buffering=1) if path else None
        self._t0, self._tel = time.monotonic(), 0
        self._note(f"open {port}")
        try:   # exclusive: a second program on the same port would silently steal replies (macOS allows sharing)
            self._ser = serial.Serial(port, 115200, timeout=timeout, exclusive=True)
        except serial.SerialException as e:
            if "exclusively lock" in str(e):
                raise serial.SerialException(f"{port} is busy: another program has it open "
                                             f"(a running `bumpem serve`, monitor or test script?)") from None
            raise

    def _note(self, text: str) -> None:
        if self._log:
            self._log.write(f"{time.monotonic() - self._t0:9.3f}  {text}\n")

    def write(self, data: bytes) -> None:
        self._note(f">> {data!r}")
        self._ser.write(data)
        self._ser.flush()
        self._note("   (written)")

    def readline(self) -> bytes:
        line = self._ser.readline()
        if self._log and line:
            if line.startswith(b"T,"):
                self._tel += 1
                if self._tel % 100 == 0:
                    self._note(f"<< ({self._tel} telemetry lines so far)")
            else:
                self._note(f"<< {line!r}")
        return line

    def close(self) -> None:
        self._ser.close()


def find_ports() -> list[str]:
    from serial.tools import list_ports
    return [p.device for p in list_ports.comports()]


class BoardError(RuntimeError):
    pass


class Board:
    """One command in flight at a time; replies are matched by command name.
    `estop()` bypasses the request lock so it is never queued behind another command."""

    def __init__(self, link: Link, timeout: float = 1.0):
        self._link, self._timeout = link, timeout
        self._req_lock, self._write_lock = threading.Lock(), threading.Lock()
        self._waiting: tuple[str, queue.Queue] | None = None
        self._extra: list[P.Info | P.Param] = []
        self._telemetry: queue.Queue[P.Telemetry] = queue.Queue(maxsize=10000)
        self._listeners: list[Callable[[P.Message], None]] = []
        self.last: P.Telemetry | None = None
        self.last_event: P.Event | None = None
        self._run = True
        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()

    # ---------- plumbing ----------
    def _write(self, line: str) -> None:
        with self._write_lock:
            self._link.write(P.encode(line))

    def _read_loop(self) -> None:
        while self._run:
            try:
                raw = self._link.readline()
            except Exception:
                if self._run:
                    raise
                return
            if not raw:
                continue
            msg = P.parse_line(raw.decode("ascii", errors="replace"))
            if isinstance(msg, P.Event):
                self.last_event = msg
            if isinstance(msg, P.Telemetry):
                self.last = msg
                try:
                    self._telemetry.put_nowait(msg)
                except queue.Full:
                    self._telemetry.get_nowait()
                    self._telemetry.put_nowait(msg)
            waiting = self._waiting
            if isinstance(msg, (P.Info, P.Param)) and waiting:
                self._extra.append(msg)
            elif isinstance(msg, P.Ack) and waiting and msg.cmd == waiting[0]:
                waiting[1].put(msg)
            for cb in self._listeners:
                cb(msg)

    def request(self, line: str) -> tuple[P.Ack, list[P.Info | P.Param]]:
        cmd = line.split()[0].upper()
        with self._req_lock:
            q: queue.Queue = queue.Queue()
            self._extra, self._waiting = [], (cmd, q)
            try:
                self._write(line)
                ack = q.get(timeout=self._timeout)
            except queue.Empty:
                raise BoardError(f"no reply to {cmd}{self._stuck_hint()}") from None
            finally:
                self._waiting = None
            if not ack.ok:
                raise BoardError(f"{cmd}: {ack.detail}")
            return ack, self._extra

    def _stuck_hint(self) -> str:
        e = self.last_event
        if e and e.kind == "FAULT" and any("DAC init failed" in a for a in e.args):
            return ("; the board is stuck at power-up: DAC (MCP4728) not found on I2C. Check its VCC, GND, "
                    "SDA (Teensy 18) and SCL (Teensy 19) wires, then unplug and replug the Teensy's USB")
        return ""

    def add_listener(self, cb: Callable[[P.Message], None]) -> None:
        """Called from the reader thread for every message (telemetry, events, acks, text)."""
        self._listeners.append(cb)

    def telemetry(self, timeout: float | None = None) -> Iterator[P.Telemetry]:
        while True:
            try:
                yield self._telemetry.get(timeout=timeout)
            except queue.Empty:
                return

    # ---------- API ----------
    def info(self) -> dict[str, str]:
        _, extra = self.request("INFO")
        return next(m.fields for m in extra if isinstance(m, P.Info))

    def stats(self) -> dict[str, str]:
        _, extra = self.request("STATS")
        return next(m.fields for m in extra if isinstance(m, P.Info))

    def get(self, name: str | None = None) -> dict[str, float]:
        _, extra = self.request("GET" if name is None else f"GET {name}")
        return {m.name: m.value for m in extra if isinstance(m, P.Param)}

    def set(self, name: str, value: float) -> None:
        self.request(P.set_cmd(name, value))

    def configure(self, params: dict[str, float]) -> None:
        for k, v in params.items():
            self.set(k, v)

    def arm(self) -> None:
        self.request("ARM")

    def pulse(self, pulse_id: int, amps: dict[str, float], *, delay_ms: float = 0, rise_ms: float,
              dur_ms: float, fall_ms: float) -> None:
        self.request(P.pulse_cmd(pulse_id, amps, delay_ms=delay_ms, rise_ms=rise_ms,
                                 dur_ms=dur_ms, fall_ms=fall_ms))

    def abort(self) -> None:
        self.request("ABORT")

    def release(self, ms: float = 1000) -> None:
        self.request(f"RELEASE {ms:g}")

    def clear(self) -> None:
        self.request("CLEAR")

    def ping(self) -> None:
        self.request("PING")

    def estop(self) -> None:
        """Immediate: drivers off, tension lost. Not queued behind other commands."""
        self._write("ESTOP")

    def close(self) -> None:
        self._run = False
        self._link.close()
        self._reader.join(timeout=1)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

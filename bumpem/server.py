"""`bumpem serve`: HTTP + WebSocket API for the board (docs/API.md, `board` and `host` endpoints).

The server owns the serial port. Clients (UI, MATLAB, scripts) use only this API.
Interactive test page: http://127.0.0.1:8000/docs
"""
from __future__ import annotations

import asyncio
import threading
import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from . import geometry
from . import protocol as P
from .device import Board, BoardError

SERVER_VERSION = "0.2.0"
API_VERSION = "1.0"


# ---------- errors (docs/API.md "Errors") ----------
class ApiError(Exception):
    def __init__(self, code: str, status: int, message: str):
        self.code, self.status, self.message = code, status, message


def _board_error(e: BoardError) -> ApiError:
    msg = str(e)
    if msg.startswith("no reply"):
        return ApiError("board_timeout", 504, msg)
    return ApiError("board_rejected", 409, msg.split(": ", 1)[-1])


# ---------- request bodies ----------
class ConnectBody(BaseModel):
    port: str = Field(description='Serial device (see GET /ports) or "sim"', examples=["sim"])


class ReleaseBody(BaseModel):
    ms: float = Field(1000, ge=0, le=10000, description="Ramp to 0 N over this time")


class PulseBody(BaseModel):
    amps: dict[str, float] = Field(description="N above baseline per channel", examples=[{"C": 10}])
    delay_ms: float = 0
    rise_ms: float = Field(examples=[50])
    dur_ms: float = Field(description="Start to end, ramps included", examples=[600])
    fall_ms: float = Field(examples=[50])


class PerturbationBody(BaseModel):
    angle_deg: float = Field(description="Pull direction: 0 front, +90 left, -90 right, 180 back (Vicon axes)",
                             examples=[135])
    amplitude_n: float = Field(gt=0, description="Resultant force above baseline along angle_deg", examples=[20])
    phase1_ms: float = Field(ge=0, description="Acceleration phase one (ramp up)", examples=[50])
    dur_ms: float = Field(gt=0, description="Start to end, ramps included", examples=[400])
    phase2_ms: float = Field(ge=0, description="Acceleration phase two (ramp down)", examples=[50])
    delay_ms: float = Field(0, ge=0, description="Board-side delay before the start")


# ---------- shared state ----------
def _telemetry_dict(t: P.Telemetry) -> dict[str, Any]:
    return {"type": "telemetry", "t_ms": t.t_ms, "state": t.state, "pulse_id": t.pulse_id,
            "target": t.target, "measured": t.measured, "dac": t.dac}


class Hub:
    """The one board connection plus the WebSocket clients listening to it."""

    def __init__(self, wd_ms: int = 1000):
        self.wd_ms = wd_ms
        self.board: Board | None = None
        self.port: str | None = None
        self.next_pulse_id = 1
        self._clients: set[tuple[asyncio.AbstractEventLoop, asyncio.Queue]] = set()
        self._lock = threading.Lock()
        self._ping_stop = threading.Event()

    # --- connection ---
    def connect(self, port: str) -> None:
        self.disconnect()
        if port == "sim":
            from .sim import SimLink
            board = Board(SimLink())
        else:
            from .device import SerialLink
            try:
                board = Board(SerialLink(port))
            except Exception as e:  # serial.SerialException, FileNotFoundError, ...
                raise ApiError("invalid", 422, f"cannot open {port}: {e}") from None
        board.add_listener(self._dispatch)
        self.board, self.port = board, port
        if port != "sim" and self.wd_ms > 0:   # firmware aborts a pending pulse if the server dies
            self.call(board.set, "wd_ms", self.wd_ms)
            self._ping_stop.clear()
            threading.Thread(target=self._ping_loop, args=(board,), daemon=True).start()

    def disconnect(self) -> None:
        board, self.board, self.port = self.board, None, None
        self._ping_stop.set()
        if board is not None:
            board.close()

    def _ping_loop(self, board: Board) -> None:
        while not self._ping_stop.wait(0.3):
            try:
                board.ping()
            except BoardError:
                pass   # busy or late reply; the next ping retries

    def need(self) -> Board:
        if self.board is None:
            raise ApiError("not_connected", 409, "no board connected (POST /api/v1/connect)")
        return self.board

    def call(self, fn, *args, **kw):
        try:
            return fn(*args, **kw)
        except BoardError as e:
            raise _board_error(e) from None
        except ValueError as e:
            raise ApiError("invalid", 422, str(e)) from None

    # --- live stream ---
    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=2000)
        with self._lock:
            self._clients.add((asyncio.get_running_loop(), q))
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        with self._lock:
            self._clients = {c for c in self._clients if c[1] is not q}

    def _dispatch(self, msg: P.Message) -> None:   # board reader thread
        if isinstance(msg, P.Telemetry):
            item = _telemetry_dict(msg)
        elif isinstance(msg, P.Event):
            item = {"type": "event", "t_ms": msg.t_ms, "kind": msg.kind, "args": list(msg.args)}
        else:
            return
        with self._lock:
            clients = list(self._clients)
        for loop, q in clients:
            loop.call_soon_threadsafe(_put_drop, q, item)


def _put_drop(q: asyncio.Queue, item: dict) -> None:
    try:
        q.put_nowait(item)
    except asyncio.QueueFull:
        pass


# ---------- app ----------
def create_app(wd_ms: int = 1000, board: str | None = None) -> FastAPI:
    hub = Hub(wd_ms)

    @asynccontextmanager
    async def lifespan(_):
        if board:
            hub.connect(board)
        yield
        hub.disconnect()

    app = FastAPI(title="bumpem server", version=SERVER_VERSION, lifespan=lifespan,
                  description="Board API of docs/API.md. Stop the treadmill before `release` or `estop`.")
    app.state.hub = hub

    @app.exception_handler(ApiError)
    async def _api_error(_, e: ApiError):
        return JSONResponse({"error": {"code": e.code, "message": e.message}}, status_code=e.status)

    @app.exception_handler(RequestValidationError)
    async def _invalid(_, e: RequestValidationError):
        return JSONResponse({"error": {"code": "invalid", "message": str(e.errors())}}, status_code=422)

    # --- connection ---
    @app.get("/api/v1/info")
    def info():
        b = hub.board
        return {"server": SERVER_VERSION, "api": API_VERSION, "port": hub.port,
                "board": hub.call(b.info) if b else None}

    @app.get("/api/v1/ports")
    def ports():
        from .device import find_ports
        return find_ports()

    @app.post("/api/v1/connect")
    def connect(body: ConnectBody):
        hub.connect(body.port)
        return info()

    @app.post("/api/v1/disconnect")
    def disconnect():
        hub.disconnect()
        return {}

    # --- state and parameters ---
    @app.get("/api/v1/status")
    def status():
        b = hub.need()
        t = b.last
        return {"port": hub.port, "state": t.state if t else None, "pulse_id": t.pulse_id if t else 0,
                "telemetry": _telemetry_dict(t) if t else None}

    @app.get("/api/v1/params")
    def params():
        return hub.call(hub.need().get)

    @app.patch("/api/v1/params")
    def patch_params(body: dict[str, float]):
        b = hub.need()
        for name, value in body.items():   # one by one, stop at the first rejection
            try:
                b.set(name, value)
            except BoardError as e:
                err = _board_error(e)
                raise ApiError(err.code, err.status, f"{name}: {err.message}") from None
        return hub.call(b.get)

    # --- actions ---
    @app.post("/api/v1/arm")
    def arm():
        hub.call(hub.need().arm)
        return {}

    @app.post("/api/v1/abort")
    def abort():
        hub.call(hub.need().abort)
        return {}

    @app.post("/api/v1/release")
    def release(body: ReleaseBody | None = None):
        hub.call(hub.need().release, (body or ReleaseBody()).ms)
        return {}

    @app.post("/api/v1/estop")
    def estop():
        hub.need().estop()   # not queued behind other requests
        return {}

    @app.post("/api/v1/clear")
    def clear():
        hub.call(hub.need().clear)
        return {}

    def send_pulse(amps: dict[str, float], delay_ms: float, rise_ms: float, dur_ms: float, fall_ms: float) -> int:
        b = hub.need()
        pid = hub.next_pulse_id
        hub.call(b.pulse, pid, amps, delay_ms=delay_ms, rise_ms=rise_ms, dur_ms=dur_ms, fall_ms=fall_ms)
        hub.next_pulse_id += 1
        return pid

    def enabled_modules() -> set[str]:
        p = hub.call(hub.need().get)
        return {m for m in geometry.MODULE_ANGLE_DEG if p.get(f"ch_{m}", 0) >= 1}

    @app.post("/api/v1/pulse")
    def pulse(body: PulseBody):
        pid = send_pulse({k.upper(): v for k, v in body.amps.items()}, body.delay_ms, body.rise_ms,
                         body.dur_ms, body.fall_ms)
        return {"pulse_id": pid}

    # --- host layer ---
    @app.get("/api/v1/geometry")
    def get_geometry():
        on = enabled_modules() if hub.board is not None else None
        return {"convention": geometry.CONVENTION,
                "modules": {m: {"angle_deg": a, "enabled": None if on is None else m in on}
                            for m, a in geometry.MODULE_ANGLE_DEG.items()},
                "reachable": None if on is None else geometry.reachable(on)}

    @app.post("/api/v1/perturbation")
    def perturbation(body: PerturbationBody):
        try:
            amps = geometry.split(body.angle_deg, body.amplitude_n, enabled_modules())
        except ValueError as e:
            raise ApiError("invalid", 422, str(e)) from None
        pid = send_pulse(amps, body.delay_ms, body.phase1_ms, body.dur_ms, body.phase2_ms)
        return {"pulse_id": pid, "amps": amps}

    # --- live stream ---
    @app.websocket("/api/v1/stream")
    async def stream(ws: WebSocket, telemetry_hz: float = Query(30, gt=0, le=1000)):
        await ws.accept()
        q = hub.subscribe()
        period, last_t = 1.0 / telemetry_hz, 0.0

        async def receive():
            while True:
                msg = await ws.receive_json()
                if isinstance(msg, dict) and msg.get("type") == "estop" and hub.board is not None:
                    hub.board.estop()

        rx = asyncio.create_task(receive())
        try:
            while not rx.done():
                try:
                    item = await asyncio.wait_for(q.get(), timeout=0.5)
                except asyncio.TimeoutError:
                    continue
                if item["type"] == "telemetry":
                    now = time.monotonic()
                    if now - last_t < period:
                        continue
                    last_t = now
                await ws.send_json(item)
        except WebSocketDisconnect:
            pass
        finally:
            rx.cancel()
            hub.unsubscribe(q)

    return app

"""bumpem/clocksync.py and the server's kept connections + sync check (docs/API.md "Clocks and sync", D49)."""
import random
import time

import pytest

from bumpem.clocksync import ClockFit


def _feed(fit, seconds, rate=100, drift_ppm=50.0, offset=100.0, dev0=0.0, seed=1):
    """Device clock running drift_ppm fast; arrival = true PC time + 0.5 ms + exponential jitter (mean 2 ms)."""
    rng = random.Random(seed)
    for k in range(int(seconds * rate)):
        dev = dev0 + k / rate
        true_pc = offset + dev * (1 - drift_ppm * 1e-6)
        fit.add(dev, true_pc + 0.0005 + rng.expovariate(1 / 0.002))
    return lambda dev: offset + dev * (1 - drift_ppm * 1e-6) + 0.0005


def test_fit_offset_drift_jitter():
    fit = ClockFit()
    assert fit.to_pc(1.0) is None and fit.status(0) is None
    true = _feed(fit, 30)
    st = fit.status(true(30))
    assert st["drift_ppm"] == pytest.approx(-50, abs=8) and st["span_s"] >= 27   # newest bin not in the fit yet
    assert st["jitter_ms"] < 0.3 and st["late_ms"] > 1                     # minima tight, arrivals spread
    for dev in (5.0, 15.0, 29.0):
        assert abs(fit.to_pc(dev) - true(dev)) < 0.0003                     # within 0.3 ms of the least-delayed arrival


def test_offset_only_first_seconds_and_reset():
    fit = ClockFit()
    true = _feed(fit, 1.5)
    assert fit.status(0) is None and abs(fit.to_pc(1.0) - true(1.0)) < 0.002
    _feed(fit, 5, dev0=0.0, offset=500.0)                                   # device clock restarted: new fit
    assert abs(fit.to_pc(1.0) - (500 + 1.0 + 0.0005)) < 0.003


pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from bumpem import server  # noqa: E402


def _until(fn, timeout):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if fn():
            return True
        time.sleep(0.05)
    return False


def test_bad_port_at_startup_keeps_server_and_retries(monkeypatch):
    monkeypatch.setattr(server, "RETRY_S", 0.3)
    with TestClient(server.create_app(board="/dev/no_such_teensy")) as c:
        s = c.get("/api/v1/sync").json()
        assert not s["board"]["connected"] and s["board"]["target"] == "/dev/no_such_teensy"
        assert "cannot open" in s["board"]["message"] and not s["in_sync"]
        c.post("/api/v1/disconnect")                                       # stops the retries
        assert c.get("/api/v1/sync").json()["board"]["target"] is None


def test_lost_board_reconnects_and_sync(monkeypatch):
    monkeypatch.setattr(server, "RETRY_S", 0.3)
    with TestClient(server.create_app(board="sim", vicon="sim")) as c:
        hub = c.app.state.hub
        s = c.get("/api/v1/sync").json()
        assert s["board"]["connected"] and s["vicon"]["connected"] and not s["in_sync"]   # no clock yet
        old = hub.board
        old._link.readline = lambda: (time.sleep(0.01), b"")[1]             # link goes silent (cable pulled)
        assert _until(lambda: hub.board is not old and hub.board is not None, 4)
        assert _until(lambda: c.get("/api/v1/sync").json()["in_sync"], 9), c.get("/api/v1/sync").json()["problems"]
        s = c.get("/api/v1/sync").json()
        assert s["board"]["clock"]["ok"] and s["vicon"]["clock"]["lost_frames"] == 0 and s["board"]["message"] is None

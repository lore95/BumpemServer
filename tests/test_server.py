"""Server API against the real-time simulator (docs/API.md, board endpoints)."""
import time

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from bumpem.server import create_app  # noqa: E402


@pytest.fixture
def client():
    with TestClient(create_app()) as c:
        yield c


@pytest.fixture
def sim(client):
    assert client.post("/api/v1/connect", json={"port": "sim"}).status_code == 200
    return client


def err(r):
    return r.json()["error"]["code"]


def test_not_connected(client):
    r = client.post("/api/v1/arm")
    assert r.status_code == 409 and err(r) == "not_connected"
    assert client.get("/api/v1/info").json()["board"] is None


def test_info_and_params(sim):
    info = sim.get("/api/v1/info").json()
    assert info["api"] == "1.0" and info["board"]["proto"] == "1"
    p = sim.get("/api/v1/params").json()
    assert p["kff"] == 7.5 and len(p) == 32
    p = sim.patch("/api/v1/params", json={"kff": 2, "baseline_n": 3}).json()
    assert p["kff"] == 2 and p["baseline_n"] == 3


def test_params_rejection_names_key(sim):
    r = sim.patch("/api/v1/params", json={"kff": 3, "fmax_n": 250})
    assert r.status_code == 409 and err(r) == "board_rejected"
    assert r.json()["error"]["message"].startswith("fmax_n:")
    assert sim.get("/api/v1/params").json()["kff"] == 3   # applied before the rejection


def test_invalid_body(sim):
    r = sim.post("/api/v1/pulse", json={"amps": {"C": 10}})
    assert r.status_code == 422 and err(r) == "invalid"
    r = sim.post("/api/v1/pulse", json={"amps": {"C": 10}, "rise_ms": 400, "dur_ms": 600, "fall_ms": 300})
    assert r.status_code == 422 and err(r) == "invalid"


def test_pulse_disarmed_rejected(sim):
    r = sim.post("/api/v1/pulse", json={"amps": {"C": 10}, "rise_ms": 50, "dur_ms": 600, "fall_ms": 50})
    assert r.status_code == 409 and err(r) == "board_rejected"
    assert "not armed" in r.json()["error"]["message"]


def wait_state(client, state, timeout=3.0):
    end = time.time() + timeout
    while time.time() < end:
        s = client.get("/api/v1/status").json()
        if s["state"] == state:
            return s
        time.sleep(0.05)
    pytest.fail(f"state {state} not reached: {s}")


def test_arm_pulse_abort_estop(sim):
    sim.patch("/api/v1/params", json={"arm_ms": 0})
    assert sim.post("/api/v1/arm").status_code == 200
    wait_state(sim, "ARMED")
    r1 = sim.post("/api/v1/pulse", json={"amps": {"c": 10}, "rise_ms": 0, "dur_ms": 50, "fall_ms": 0})
    assert r1.json() == {"pulse_id": 1}
    time.sleep(0.2)
    r2 = sim.post("/api/v1/pulse", json={"amps": {"C": 10}, "rise_ms": 0, "dur_ms": 1000, "fall_ms": 0})
    assert r2.json() == {"pulse_id": 2}
    assert sim.post("/api/v1/abort").status_code == 200
    assert sim.post("/api/v1/estop").status_code == 200
    wait_state(sim, "ESTOP")


def test_stream_telemetry_and_estop(sim):
    with sim.websocket_connect("/api/v1/stream?telemetry_hz=50") as ws:
        msg = ws.receive_json()
        while msg["type"] != "telemetry":
            msg = ws.receive_json()
        assert set(msg["target"]) == {"A", "B", "C", "D"}
        ws.send_json({"type": "estop"})
        for _ in range(200):
            msg = ws.receive_json()
            if msg["type"] == "event" and msg["kind"] == "STATE" and msg["args"] == ["ESTOP"]:
                break
        else:
            pytest.fail("no ESTOP event")

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


def test_geometry_without_board(client):
    g = client.get("/api/v1/geometry").json()
    assert g["modules"]["D"] == {"angle_deg": 180.0, "enabled": None} and g["reachable"] is None


def test_perturbation_split_and_reach(sim):
    # setup 2026-10-02: A left, C right, D back; B (front) not installed
    sim.patch("/api/v1/params", json={"ch_A": 1, "ch_B": 0, "ch_C": 1, "ch_D": 1, "arm_ms": 0})
    g = sim.get("/api/v1/geometry").json()
    assert g["reachable"] == [{"from_deg": 90.0, "to_deg": -90.0}] and g["modules"]["B"]["enabled"] is False

    r = sim.post("/api/v1/perturbation", json={"angle_deg": 45, "amplitude_n": 20,
                                               "phase1_ms": 50, "dur_ms": 400, "phase2_ms": 50})
    assert r.status_code == 422 and err(r) == "invalid" and "module B" in r.json()["error"]["message"]

    sim.post("/api/v1/arm")
    wait_state(sim, "ARMED")
    base = sim.get("/api/v1/params").json()["baseline_n"]
    r = sim.post("/api/v1/perturbation", json={"angle_deg": 135, "amplitude_n": 20,
                                               "phase1_ms": 0, "dur_ms": 300, "phase2_ms": 0})
    assert r.status_code == 200
    assert r.json() == {"pulse_id": 1, "amps": {"A": 14.14, "D": 14.14}}
    end = time.time() + 2
    while time.time() < end:                       # board target reaches baseline + split amplitude
        t = sim.get("/api/v1/status").json()["telemetry"]["target"]
        if t["D"] > base + 14 and t["A"] > base + 14:
            break
        time.sleep(0.02)
    else:
        pytest.fail(f"pulse not seen in targets: {t}")
    assert t["B"] == pytest.approx(0, abs=0.01) or t["B"] <= base     # B untouched

    r = sim.post("/api/v1/perturbation", json={"angle_deg": 135, "amplitude_n": 20,
                                               "phase1_ms": 0, "dur_ms": 300, "phase2_ms": 0})
    assert r.status_code == 409 and r.json()["error"]["message"] == "busy"   # one pulse at a time (firmware)
    time.sleep(0.4)
    wait_state(sim, "ARMED")
    r = sim.post("/api/v1/perturbation", json={"angle_deg": 270, "amplitude_n": 10,
                                               "phase1_ms": 0, "dur_ms": 100, "phase2_ms": 0})
    assert r.status_code == 200, r.json()
    assert r.json()["amps"] == {"C": 10}


def test_ui_served_when_folder_exists(tmp_path):
    (tmp_path / "index.html").write_text("<title>ui</title>")
    with TestClient(create_app(ui_dir=str(tmp_path))) as c:
        r = c.get("/", follow_redirects=False)
        assert r.status_code in (302, 307) and r.headers["location"] == "/ui/"
        assert "<title>ui</title>" in c.get("/ui/").text
    with TestClient(create_app(ui_dir=str(tmp_path / "missing"))) as c:
        assert c.get("/ui/").status_code == 404


def test_modules_set_at_connect():
    with TestClient(create_app(modules="ACD")) as c:
        c.post("/api/v1/connect", json={"port": "sim"})
        p = c.get("/api/v1/params").json()
        assert (p["ch_A"], p["ch_B"], p["ch_C"], p["ch_D"]) == (1, 0, 1, 1)
        assert c.get("/api/v1/geometry").json()["reachable"] == [{"from_deg": 90.0, "to_deg": -90.0}]


def test_modules_applied_once_disarmed():
    app = create_app()
    with TestClient(app) as c:
        hub = app.state.hub
        c.post("/api/v1/connect", json={"port": "sim"})
        c.patch("/api/v1/params", json={"arm_ms": 0})
        c.post("/api/v1/arm")
        wait_state(c, "ARMED")
        hub.modules = "ACD"
        hub.apply_modules()                      # armed: channels can't change yet
        assert hub.modules_pending
        c.post("/api/v1/release", json={"ms": 0})
        end = time.time() + 3
        while time.time() < end and hub.modules_pending:
            time.sleep(0.05)
        p = c.get("/api/v1/params").json()
        assert not hub.modules_pending and (p["ch_B"], p["ch_D"]) == (0, 1)


def test_concurrent_connects_leave_one_working_board():
    import threading
    app = create_app()
    with TestClient(app) as c:
        hub = app.state.hub
        ts = [threading.Thread(target=hub.connect, args=("sim",)) for _ in range(4)]
        for t in ts:
            t.start()
        for t in ts:
            t.join(timeout=10)
        assert c.get("/api/v1/info").json()["board"]["proto"] == "1"


def test_testing_mode_pull_restores_everything():
    app = create_app(mode="testing", modules="ACD")
    with TestClient(app) as c:
        c.post("/api/v1/connect", json={"port": "sim"})
        before = c.get("/api/v1/params").json()
        peak = {"C": 0.0, "A": 0.0}
        app.state.hub.board.add_listener(
            lambda m: [peak.__setitem__(k, max(peak[k], m.target[k])) for k in peak] if hasattr(m, "target") else None)
        r = c.post("/api/v1/test/pull", json={"module": "c", "force_n": 5, "dur_ms": 300})
        assert r.status_code == 200, r.json()
        assert r.json()["module"] == "C"
        assert peak["C"] == pytest.approx(5, abs=0.2) and peak["A"] == 0      # only C pulled, from 0 N to 5 N
        assert c.get("/api/v1/status").json()["state"] == "DISARMED"
        assert c.get("/api/v1/params").json() == before                        # every parameter restored
        assert c.get("/api/v1/info").json()["mode"] == "testing"


def test_modes_refuse_each_other():
    with TestClient(create_app(mode="testing")) as c:
        c.post("/api/v1/connect", json={"port": "sim"})
        for path, body in [("/api/v1/arm", None), ("/api/v1/pulse", {"amps": {"C": 5}, "rise_ms": 0, "dur_ms": 100, "fall_ms": 0})]:
            r = c.post(path, json=body)
            assert r.status_code == 409 and err(r) == "wrong_mode"
    with TestClient(create_app()) as c:
        c.post("/api/v1/connect", json={"port": "sim"})
        r = c.post("/api/v1/test/pull", json={"module": "C", "force_n": 5, "dur_ms": 300})
        assert r.status_code == 409 and err(r) == "wrong_mode"

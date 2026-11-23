"""bumpem/gaitcheck.py: live touch-down / foot-off / phase moments without a board (docs/API.md "Gait check", D58)."""
import math
import time

import pytest

pytest.importorskip("pydantic")
from bumpem.gaitcheck import GaitCheck, GaitCheckBody  # noqa: E402
from bumpem.vicon import SimReader  # noqa: E402

STRIDE, STANCE, RIGHT_OFFSET = 0.72, 0.25, 0.36   # SimReader: stride, contact (half sine, peak 1500 N), right foot later
PLATES = {"left": "Left", "right": "Right"}


@pytest.fixture(autouse=True)
def no_noise(monkeypatch):
    monkeypatch.setattr("bumpem.vicon.random.gauss", lambda mu, sd: 0.0)


def feed(**cfg):
    """Simulator belts at 1000 Hz, plate clock = PC clock, `now` = the latest sample (age 0 at the frame)."""
    items, rows, clock = [], [], [0.0]
    gc = GaitCheck(GaitCheckBody(**cfg), PLATES, items.append, lambda k, d: rows.append(k), lambda t: t, lambda: clock[0])

    def run(seconds):
        t0 = clock[0]
        for k in range(1, int(seconds * 1000) + 1):
            t = round(t0 + k / 1000, 6)
            clock[0] = t
            gc.on_samples([(t, {"Left": SimReader.fz(t, 0), "Right": SimReader.fz(t, RIGHT_OFFSET)})], t)
    return gc, items, rows, run


def test_running_sides_contacts_and_phase():
    gc, items, rows, run = feed(mode="running", mass_kg=80, trigger_side="left", gait_phase_pct=20)
    run(6)
    time.sleep(0.5)                                     # phase timers (≤ ~150 ms each)
    td = [i for i in items if i["event"] == "TD"]
    assert [i["side"] for i in td[:6]] == ["left", "right"] * 3 and rows.count("GAITCHECK") == len(items)
    s = gc.status()
    assert s["detector"] == "sum" and s["fitted"] and s["thresholds"]["left"] == {"td_n": 196.2, "fo_n": 78.5}
    for side in ("left", "right"):
        assert s[side]["stride_ms"] == pytest.approx(STRIDE * 1000, abs=2)
        assert s[side]["contact_ms"] == pytest.approx(STANCE * 1000 - 14.6, abs=2)       # 196.2 → 78.5 N on the half sine
    ph = [i for i in items if i["event"] == "PHASE"]
    assert ph and all(i["side"] == "left" for i in ph)
    for p in ph:                                        # 20 % of the stride after that left touch-down
        t_td = max(i["t_pc"] for i in td if i["side"] == "left" and i["t_pc"] < p["t_pc"])
        assert (p["t_pc"] - t_td) * 1000 == pytest.approx(0.2 * STRIDE * 1000, abs=2) and p["next_contact"] == 0
    gc.stop()
    n = len(items)
    run(1)
    assert len(items) == n                              # stopped: nothing more


def test_walking_thresholds_from_first_10_s():
    gc, items, rows, run = feed(mass_kg=80, trigger_side="any", gait_phase_pct=50, gait_phase_of="stance")
    run(9)
    assert not gc.status()["fitted"] and gc.status()["thresholds"]["left"] == {"td_n": 100.0, "fo_n": 25.0}
    run(4)
    s = gc.status()
    assert s["fitted"] and s["detector"] == "plates" and s["thresholds"]["right"] == {"td_n": 20, "fo_n": 10}
    assert any(i["event"] == "STATUS" and i["fitted"] for i in items)
    time.sleep(0.5)
    ph = [i for i in items if i["event"] == "PHASE"]
    assert {i["side"] for i in ph} == {"left", "right"}
    assert all(math.isclose(i["phase_ms"], 0.5 * s[i["side"]]["contact_ms"], abs_tol=3) for i in ph[-2:])


def test_server_gaitcheck(tmp_path):
    """Plates only (sim Vicon, real time), no board."""
    from fastapi.testclient import TestClient
    from bumpem.server import create_app
    with TestClient(create_app(log_dir=str(tmp_path))) as c:
        api = "/api/v1"
        assert c.get(f"{api}/gaitcheck").json() == {"running": False}
        assert c.post(f"{api}/gaitcheck", json={"mass_kg": 80, "mode": "running"}).status_code == 409   # no Vicon
        assert c.post(f"{api}/vicon/connect", json={"host": "sim"}).status_code == 200
        s = c.post(f"{api}/gaitcheck", json={"mass_kg": 80, "mode": "running"}).json()
        assert s["running"] and s["plates"] == PLATES and s["trigger_side"] == "left"
        with c.websocket_connect(f"{api}/stream") as ws:
            seen = set()
            end = time.monotonic() + 5
            while seen != {"TD", "FO", "PHASE"} and time.monotonic() < end:
                m = ws.receive_json()
                if m["type"] == "gaitcheck":
                    seen.add(m["event"])
        assert seen == {"TD", "FO", "PHASE"}
        s = c.delete(f"{api}/gaitcheck").json()
        assert not s["running"] and s["left"]["stride_ms"] == pytest.approx(720, abs=5)

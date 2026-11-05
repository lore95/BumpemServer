"""bumpem/study.py: gait pattern, block runner, perturbation timing (docs/API.md "Study", D44)."""
import random
import time

import pytest

pytest.importorskip("pydantic")
from bumpem.study import Protocol, Study, default_plates  # noqa: E402
from bumpem.vicon import SimReader  # noqa: E402

STRIDE, RIGHT_OFFSET = 0.72, 0.36           # SimReader: stride 0.72 s, right foot half a stride later


def block(**kw):
    b = {"speed_ms": 2.5, "n_perturbations": 3, "directions_deg": [90], "intensity_pct_bw": 10, "phase1_ms": 50,
         "dur_ms": 400, "phase2_ms": 50, "trigger_side": "left", "gait_phase_pct": 25, "timing_mode": "random",
         "interval_min_steps": 4, "interval_max_steps": 4}
    return {**b, **kw}


def protocol(*blocks):
    return Protocol(subject={"subject_id": "S1", "mass_kg": 80}, blocks=list(blocks or [block()]))


class Run:
    """A Study fed with the simulator's two belts at 1000 Hz (no noise: deterministic)."""

    def __init__(self, p):
        self.sent, self.items, self.rows, self.t = [], [], [], 0.0
        self.st = Study(p, ["Left", "Right"], self.send, self.items.append, lambda k, d: self.rows.append((k, d)),
                        rng=random.Random(1))

    def send(self, pert):
        self.sent.append({**pert, "t": self.t})
        return len(self.sent)

    def run(self, seconds):
        end = self.t + seconds
        while self.t < end:
            self.t = round(self.t + 0.001, 6)
            fz = {"Left": SimReader.fz(self.t, 0), "Right": SimReader.fz(self.t, RIGHT_OFFSET)}
            self.st.on_samples([(self.t, fz)])


@pytest.fixture(autouse=True)
def no_noise(monkeypatch):
    monkeypatch.setattr("bumpem.vicon.random.gauss", lambda mu, sd: 0.0)


def test_default_plates():
    assert default_plates(["Left", "Right"]) == {"left": "Left", "right": "Right"}
    assert default_plates(["Plate 1", "Plate 2"]) == {"left": "Plate 1", "right": "Plate 2"}
    with pytest.raises(ValueError):
        default_plates(["Plate 1"])


def test_block_validation():
    with pytest.raises(ValueError, match="interval_max_steps"):
        protocol(block(interval_min_steps=9, interval_max_steps=4))
    with pytest.raises(ValueError, match="schedule_steps has 2"):
        protocol(block(timing_mode="predefined", schedule_steps=[3, 9]))
    with pytest.raises(ValueError, match="increasing"):
        protocol(block(timing_mode="predefined", schedule_steps=[3, 9, 9]))
    p = protocol(block(extra_key="kept"))
    assert p.blocks[0].model_dump()["extra_key"] == "kept"


def test_gait_pattern_then_random_block():
    r = Run(protocol())
    with pytest.raises(RuntimeError, match="gait pattern at 2.5"):
        r.st.start()
    r.st.record_gait(6)
    assert r.st.status()["state"] == "gait"
    r.run(6.01)
    s = r.st.status()
    assert s["state"] == "ready" and s["message"] is None
    for side in ("left", "right"):
        assert s["gait"][side]["stride_ms"] == pytest.approx(STRIDE * 1000, abs=2) and s["gait"][side]["n"] >= 5
    r.st.start()
    r.run(12)
    assert len(r.sent) == 3 and r.st.state == "finished"
    for k, p in enumerate(r.sent):
        assert p["amplitude_n"] == pytest.approx(78.48) and p["angle_deg"] == 90
        assert p["delay_ms"] == pytest.approx(0.25 * STRIDE * 1000, abs=1)
        assert (p["t"] % STRIDE) < 0.02                          # at a left foot strike (250 N reached ~13 ms after contact)
    steps = [d["step"] for k, d in r.rows if k == "PERT"]
    assert steps[1] - steps[0] in (4, 5) and steps[2] - steps[1] in (4, 5)   # 4 steps due, then the next left strike


def test_predefined_any_side_warmup_and_two_blocks():
    b1 = block(timing_mode="predefined", schedule_steps=[2, 6], n_perturbations=2, trigger_side="any",
               directions_deg=[90, -90])
    b2 = block(speed_ms=3.0, warmup_s=2)
    r = Run(protocol(b1, b2))
    r.st.record_gait(6); r.run(6.01)
    r.st.start(); r.run(6)
    assert [d["step"] for k, d in r.rows if k == "PERT"] == [2, 6]
    assert sorted(p["angle_deg"] for p in r.sent) == [-90, 90]
    assert r.st.state == "block_done"
    with pytest.raises(RuntimeError, match="3 m/s"):             # block 2 runs at another speed
        r.st.start()
    r.st.record_gait(6); r.run(6.01)
    assert r.st.state == "block_done" and r.st.status()["gait"]["speed_ms"] == 3.0
    r.st.start()
    assert r.st.status()["block"] == 2
    r.run(1.9)
    assert len(r.sent) == 2                                      # warm-up: nothing in the first 2 s
    r.run(10)
    assert len(r.sent) == 5 and r.st.state == "finished"


def test_stop_resume_and_refused_pulse():
    r = Run(protocol(block(n_perturbations=4)))
    r.st.record_gait(6); r.run(6.01)
    r.st.start(); r.run(4)
    n = len(r.sent)
    r.st.stop("board ESTOP")
    assert r.st.state == "stopped" and r.st.message == "board ESTOP"
    r.run(4)
    assert len(r.sent) == n                                      # nothing while stopped
    r.st.start()
    assert r.st.status()["done"] == n                            # resumed, not restarted
    r.send = lambda pert: (_ for _ in ()).throw(ValueError("module A off"))
    r.st._send = r.send
    r.run(5)
    assert r.st.state == "stopped" and "module A off" in r.st.message


def test_too_few_strides():
    r = Run(protocol())
    r.st.record_gait(2)                                          # 2 s: ~2 strides per side
    r.run(2.01)
    assert r.st.state == "loaded" and "too few strides" in r.st.message and r.st.gait is None


def test_server_study_with_simulated_board_and_plates():
    """End to end: sim board + sim plates (real time, ~8 s)."""
    from fastapi.testclient import TestClient
    from bumpem.server import create_app
    with TestClient(create_app()) as c:
        api = "/api/v1"
        body = {"subject": {"subject_id": "S1", "mass_kg": 30},
                "blocks": [block(n_perturbations=2, interval_min_steps=1, interval_max_steps=1)]}
        assert c.post(f"{api}/study", json=body).status_code == 409          # no Vicon yet
        assert c.post(f"{api}/connect", json={"port": "sim"}).status_code == 200
        assert c.post(f"{api}/vicon/connect", json={"host": "sim"}).status_code == 200
        assert c.post(f"{api}/study", json={**body, "blocks": [block(interval_min_steps=9)]}).status_code == 422
        s = c.post(f"{api}/study", json=body).json()
        assert s["state"] == "loaded" and s["plates"] == {"left": "Left", "right": "Right"}
        assert c.post(f"{api}/study/gait", json={"duration_s": 5}).json()["state"] == "gait"
        end = time.monotonic() + 8
        while c.get(f"{api}/study").json()["state"] == "gait" and time.monotonic() < end:
            time.sleep(0.2)
        s = c.get(f"{api}/study").json()
        assert s["state"] == "ready", s
        r = c.post(f"{api}/study/start")
        assert r.status_code == 409 and "Arm first" in r.json()["error"]["message"]
        c.patch(f"{api}/params", json={"fmax_n": 100})
        assert c.post(f"{api}/arm").status_code == 200
        end = time.monotonic() + 4
        while c.get(f"{api}/status").json()["state"] != "ARMED" and time.monotonic() < end:
            time.sleep(0.05)
        assert c.post(f"{api}/study/start").json()["state"] == "running"
        end = time.monotonic() + 6
        while c.get(f"{api}/study").json()["state"] == "running" and time.monotonic() < end:
            time.sleep(0.2)
        s = c.get(f"{api}/study").json()
        assert s["state"] == "finished" and s["done"] == 2, s
        c.post(f"{api}/estop")

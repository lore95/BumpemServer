"""bumpem/study.py: gait pattern, block runner, perturbation timing (docs/API.md "Study", D44)."""
import random
import time

import pytest

pytest.importorskip("pydantic")
from bumpem.gait import FO, TD, ContactDetector, fit_thresholds  # noqa: E402
from bumpem.study import Protocol, Study, default_plates  # noqa: E402
from bumpem.vicon import SimReader  # noqa: E402

STRIDE, RIGHT_OFFSET = 0.72, 0.36           # SimReader: stride 0.72 s, right foot half a stride later
STANCE = 0.25                               # SimReader: contact 0.25 s (half sine, peak 1500 N)


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

    def ready(self, seconds=6):
        self.st.record_gait(seconds)
        self.run(seconds + 0.01)


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
    assert s["state"] == "ready" and s["message"] is None and s["gait"]["rate_hz"] == 1000
    for side in ("left", "right"):
        g = s["gait"][side]
        assert g["stride_ms"] == pytest.approx(STRIDE * 1000, abs=2) and g["n"] >= 5
        assert g["td_n"] == 20 and g["fo_n"] == 10                   # no noise: the lowest thresholds
        assert g["stance_ms"] == pytest.approx(STANCE * 1000, abs=3)
    r.st.start()
    r.run(12)
    assert len(r.sent) == 3 and r.st.state == "finished"
    for k, p in enumerate(r.sent):
        assert p["amplitude_n"] == pytest.approx(78.48) and p["angle_deg"] == 90
        assert p["delay_ms"] == pytest.approx(0.25 * STANCE * 1000, abs=2)   # 25 % of the stance
        assert (p["t"] % STRIDE) < 0.005                         # at a left touch-down (20 N: ~1 ms after contact)
    steps = [d["step"] for k, d in r.rows if k == "PERT"]
    assert steps[1] - steps[0] in (4, 5) and steps[2] - steps[1] in (4, 5)   # 4 steps due, then the next left strike


def test_predefined_any_side_warmup_and_two_blocks():
    b1 = block(timing_mode="predefined", schedule_steps=[2, 6], n_perturbations=2, trigger_side="any",
               directions_deg=[90, -90])
    b2 = block(speed_ms=3.0, warmup_s=2)
    r = Run(protocol(b1, b2))
    r.ready()
    r.st.start(); r.run(6)
    assert [d["step"] for k, d in r.rows if k == "PERT"] == [2, 6]
    assert sorted(p["angle_deg"] for p in r.sent) == [-90, 90]
    assert r.st.state == "block_done"
    with pytest.raises(RuntimeError, match="3 m/s"):             # block 2 runs at another speed
        r.st.start()
    r.ready()
    assert r.st.state == "block_done" and r.st.status()["gait"]["speed_ms"] == 3.0
    r.st.start()
    assert r.st.status()["block"] == 2
    r.run(1.9)
    assert len(r.sent) == 2                                      # warm-up: nothing in the first 2 s
    r.run(10)
    assert len(r.sent) == 5 and r.st.state == "finished"


def test_stop_resume_and_refused_pulse():
    r = Run(protocol(block(n_perturbations=4)))
    r.ready()
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


def test_contact_detector_hysteresis():
    d = ContactDetector(100, 25)
    seq = [150, 50, 120, 60, 30, 20, 30, 110, 90, 24]           # starts loaded: waits for < 100 first
    assert [d.update(i, f) for i, f in enumerate(seq)] == ["", "", TD, "", "", FO, "", TD, "", FO]


def _plate(seconds, noise_sd=0.0, spikes=0.0, seed=2):
    rng = random.Random(seed)
    t = [k / 1000 for k in range(1, int(seconds * 1000))]
    fz = []
    for ti in t:
        f = SimReader.fz(ti, 0) + rng.gauss(0, noise_sd)
        if spikes and 0.4 < ti % STRIDE < 0.6 and rng.random() < 0.01:   # swing spikes
            f += spikes
        fz.append(f)
    return t, fz


def test_thresholds_from_swing_noise():
    f = fit_thresholds(*_plate(10, noise_sd=4))
    assert f["stable"] and f["noise_sd_n"] == pytest.approx(4, abs=0.5)
    assert f["td_n"] == pytest.approx(24, abs=3) and f["fo_n"] == pytest.approx(12, abs=2)
    assert sum(k == TD for k, _ in f["events"]) == 13
    f = fit_thresholds(*_plate(10, noise_sd=2, spikes=60))           # spikes above the low threshold: defaults stay
    assert not f["stable"] and (f["td_n"], f["fo_n"]) == (100, 25)


def test_phase_of_cycle_and_next_contact():
    r = Run(protocol(block(gait_phase_of="cycle", n_perturbations=1)))
    r.ready(); r.st.start(); r.run(4)
    assert r.sent[0]["delay_ms"] == pytest.approx(0.25 * STRIDE * 1000, abs=2)
    r = Run(protocol(block(gait_phase_pct=60, n_perturbations=1)))   # 60 % stance = 150 ms, latency 200 ms: next contact
    r.ready(); r.st.start(latency_ms=200); r.run(4)
    pert = [d for k, d in r.rows if k == "PERT"][0]
    assert pert["next_contact"] == 1 and pert["delay_ms"] == pytest.approx(0.6 * STANCE * 1000 - 200 + STRIDE * 1000, abs=3)
    assert any(k == "FO" for k, _ in r.rows)

"""bumpem/study.py: gait pattern, block runner, perturbation timing (docs/API.md "Study", D44)."""
import random
import zipfile
import time
from pathlib import Path

import pytest

pytest.importorskip("pydantic")
from bumpem.gait import FO, TD, ContactDetector, fit_thresholds  # noqa: E402
from bumpem.study import Protocol, Study, default_plates  # noqa: E402
from bumpem.vicon import SimReader  # noqa: E402

STRIDE, RIGHT_OFFSET = 0.72, 0.36           # SimReader: stride 0.72 s, right foot half a stride later
STANCE = 0.25                               # SimReader: contact 0.25 s (half sine, peak 1500 N)


def block(**kw):
    b = {"speed_ms": 2.5, "n_perturbations": 3, "directions_deg": [90], "intensity_pct_bw": 10, "phase1_ms": 50,
         "dur_ms": 400, "phase2_ms": 50, "trigger_side": "left", "gait_phase_pct": 25, "gait_phase_of": "stance", "timing_mode": "random",
         "interval_min_steps": 4, "interval_max_steps": 4}
    return {**b, **kw}


def protocol(*blocks):
    return Protocol(subject={"subject_id": "S1", "mass_kg": 80, "mode": "running"}, blocks=list(blocks or [block()]))


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
    s = r.st.status()
    assert (s["next_block"], s["next_speed_ms"], s["gait_ok"]) == (2, 3.0, False)
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


def test_server_study_with_simulated_board_and_plates(tmp_path):
    """End to end: sim board + sim plates (real time, ~8 s)."""
    from fastapi.testclient import TestClient
    from bumpem.server import create_app
    with TestClient(create_app(log_dir=str(tmp_path))) as c:
        api = "/api/v1"
        body = {"subject": {"subject_id": "S1", "study_name": "Knee study", "mass_kg": 30},
                "blocks": [block(n_perturbations=2, interval_min_steps=1, interval_max_steps=1)]}
        assert c.post(f"{api}/study", json=body).status_code == 409          # no Vicon yet
        assert c.post(f"{api}/connect", json={"port": "sim"}).status_code == 200
        assert c.post(f"{api}/vicon/connect", json={"host": "sim"}).status_code == 200
        assert c.post(f"{api}/study", json={**body, "blocks": [block(interval_min_steps=9)]}).status_code == 422
        s = c.post(f"{api}/study", json=body).json()
        assert s["state"] == "loaded" and s["plates"] == {"left": "Left", "right": "Right"}
        p = c.get(f"{api}/study/protocol").json()
        assert p["subject"]["mass_kg"] == 30 and p["blocks"][0]["gait_phase_of"] == "stance" and p["plates"]["left"] == "Left"
        r = c.post(f"{api}/study/gait", json={"duration_s": 5})
        assert r.status_code == 409 and "Arm first" in r.json()["error"]["message"]
        c.patch(f"{api}/params", json={"fmax_n": 100})
        assert c.post(f"{api}/arm").status_code == 200
        end = time.monotonic() + 4
        while c.get(f"{api}/status").json()["state"] != "ARMED" and time.monotonic() < end:
            time.sleep(0.05)
        assert c.post(f"{api}/study/gait", json={"duration_s": 5}).json()["state"] == "gait"
        end = time.monotonic() + 8
        while c.get(f"{api}/study").json()["state"] == "gait" and time.monotonic() < end:
            time.sleep(0.2)
        s = c.get(f"{api}/study").json()
        assert s["state"] == "ready", s
        r = c.post(f"{api}/study/start")
        assert r.status_code == 409 and "not recording" in r.json()["error"]["message"]      # D51
        c.post(f"{api}/log/start", json={"label": "e2e"})
        assert c.post(f"{api}/study/start").json()["state"] == "running"
        end = time.monotonic() + 6
        while c.get(f"{api}/study").json()["state"] == "running" and time.monotonic() < end:
            time.sleep(0.2)
        s = c.get(f"{api}/study").json()
        assert s["state"] == "finished" and s["done"] == 2, s
        time.sleep(1.2)                                                       # the last pulse runs to its end
        c.post(f"{api}/estop")
        if c.get(f"{api}/log").json()["recording"]:
            done = c.post(f"{api}/log/stop").json()
            rep = c.get(f"{api}/log/delay").json()                            # D51: the study pulls, measured
            assert [p["pulse_id"] for p in rep["pulses"]] and rep["recommended_latency_ms"] is not None
            assert all(p.get("timing_error_ms") is not None and p.get("command_ms") is not None for p in rep["pulses"]), rep["text"]
            assert Path(rep["file"]).is_file() and "recommended System delay" in rep["text"]

        c.post(f"{api}/log/start", json={"label": "after"})                  # D53: refused while recording
        assert c.post(f"{api}/study/export").status_code == 409
        c.post(f"{api}/log/stop")
        ex = c.post(f"{api}/study/export").json()                             # D53: session zip
        assert ex["name"].startswith("S1_Knee-study_") and ex["name"].endswith(".zip") and ex["recordings"] == 2, ex
        with zipfile.ZipFile(ex["file"]) as z:
            names = {n.split("/", 1)[1] for n in z.namelist()}
        assert {"protocol.json", "study.json", "params.json"} <= names
        for kind in ("force_", "events_", "vicon_", "delay_"):
            assert any(n.startswith(kind) and "e2e" in n for n in names), (kind, names)
        assert c.get(f"{api}/study/export").headers["content-type"] == "application/zip"
        saved = c.get(f"{api}/studies").json()
        assert saved[0]["subject_id"] == "S1" and saved[0]["study_name"] == "Knee study" and saved[0]["blocks"] == 1
        assert c.get(f"{api}/studies/{saved[0]['name']}/protocol").json()["subject"]["mass_kg"] == 30
        assert c.get(f"{api}/studies/nothing.zip/protocol").status_code == 404


def test_session_zip_name_and_ids():
    from datetime import datetime
    from bumpem.session import zip_name
    t = datetime(2026, 11, 19, 14, 30)
    assert zip_name("S014", "Knee study", t) == "S014_Knee-study_2026-11-19_1430"
    assert zip_name("S014", "", t) == "S014_2026-11-19_1430" and zip_name("", "", t) == "subject_2026-11-19_1430"
    with pytest.raises(ValueError):                                           # an ID, never a name with spaces
        Protocol(subject={"subject_id": "Mario Rossi", "mass_kg": 80}, blocks=[block()])


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


def test_gait_cancelled_when_board_leaves_armed():
    """Board ESTOP during the gait pattern: cancelled, back to the previous state (server, sim)."""
    from fastapi.testclient import TestClient
    from bumpem.server import create_app
    with TestClient(create_app()) as c:
        api = "/api/v1"
        c.post(f"{api}/connect", json={"port": "sim"})
        c.post(f"{api}/vicon/connect", json={"host": "sim"})
        c.post(f"{api}/study", json={"subject": {"mass_kg": 30}, "blocks": [block()]})
        c.post(f"{api}/arm")
        end = time.monotonic() + 4
        while c.get(f"{api}/status").json()["state"] != "ARMED" and time.monotonic() < end:
            time.sleep(0.05)
        assert c.post(f"{api}/study/gait", json={"duration_s": 20}).json()["state"] == "gait"
        c.post(f"{api}/estop")
        end = time.monotonic() + 2
        while c.get(f"{api}/study").json()["state"] == "gait" and time.monotonic() < end:
            time.sleep(0.05)
        s = c.get(f"{api}/study").json()
        assert s["state"] == "loaded" and "ESTOP" in s["message"]


# ---------------------------------------------------------------- D50: patterns, amplitude modes, duration, mode
def pblock(items, **kw):
    b = {k: v for k, v in block(**kw).items() if k not in ("timing_mode", "interval_min_steps", "interval_max_steps",
                                                         "directions_deg", "intensity_pct_bw")}
    return {**b, "pattern": "p", "pattern_items": [{"angle_deg": a, "gap_steps": g} for a, g in items],
            "amplitude_mode": "newton", "amplitude": 40, **kw}


def test_pattern_same_for_every_participant():
    items = [(90, 3), (-90, 4), (180, 2)]
    runs = []
    for seed in (1, 2):                                            # two participants, different random generators
        r = Run(protocol(pblock(items, trigger_side="any", n_perturbations=3)))
        r.st.rng = random.Random(seed)
        r.ready(); r.st.start(); r.run(6)
        runs.append([(d["angle_deg"], d["step"]) for k, d in r.rows if k == "PERT"])
        assert r.st.state == "finished" and all(p["amplitude_n"] == 40 for p in r.sent)
    assert runs[0] == runs[1] == [(90, 3), (-90, 7), (180, 9)]


def test_pattern_shorter_than_block_refused():
    with pytest.raises(ValueError, match="has 2 perturbations, the block wants 3"):
        Run(protocol(pblock([(90, 3), (-90, 4)], n_perturbations=3)))


def test_amplitude_modes():
    r = Run(protocol(block(), block(intensity_pct_bw=None, amplitude_mode="percent_bw", amplitude=10),
                     block(intensity_pct_bw=None, amplitude_mode="newton", amplitude=33.3)))
    assert [r.st.amplitude_n(b) for b in r.st.p.blocks] == [78.48, 78.48, 33.3]
    with pytest.raises(ValueError, match="100 % body weight"):
        protocol(block(intensity_pct_bw=None, amplitude_mode="percent_bw", amplitude=120))


def test_duration_check_and_end():
    r = Run(protocol(block(duration_s=20, n_perturbations=20)))   # gaps 4 (+1 for the left foot) at ~2.78 steps/s
    r.ready()
    with pytest.raises(RuntimeError, match="at most 11 fit"):
        r.st.start()
    r = Run(protocol(block(duration_s=10, n_perturbations=3, interval_min_steps=30, interval_max_steps=30)))
    r.ready()
    r.st.fit_check = lambda *a, **k: None                          # e.g. the subject slowed down: time runs out
    r.st.start(); r.run(11)
    assert r.st.state == "finished" and "duration 10 s reached: 0 of 3" in r.st.message


def test_warmup_steps_not_counted():
    r = Run(protocol(pblock([(90, 2)], trigger_side="any", n_perturbations=1, warmup_s=2)))
    r.ready(); r.st.start(); r.run(4)
    assert [d["step"] for k, d in r.rows if k == "PERT"] == [2]   # 2 steps after the warm-up, not from the start


def test_mode_plausibility_message():
    r = Run(Protocol(subject={"mass_kg": 80, "mode": "walking"}, blocks=[block()]))   # the simulator runs
    r.ready()
    assert r.st.state == "ready" and "does not look like walking" in r.st.message


def test_patterns_api_and_pattern_study(tmp_path):
    from fastapi.testclient import TestClient
    from bumpem.server import create_app
    with TestClient(create_app(patterns=str(tmp_path / "patterns"), log_dir=str(tmp_path))) as c:
        api = "/api/v1"
        pat = {"name": "lat-2", "items": [{"angle_deg": 270, "gap_steps": 2}, {"angle_deg": 90, "gap_steps": 2}],
               "rules": {"seed": 7}}
        saved = c.post(f"{api}/patterns", json=pat).json()
        assert saved["items"][0]["angle_deg"] == -90 and saved["created"]
        assert c.post(f"{api}/patterns", json=pat).status_code == 409             # never overwritten
        assert c.post(f"{api}/patterns", json={**pat, "name": "bad name"}).status_code == 422
        assert c.get(f"{api}/patterns").json()[0] == {"name": "lat-2", "n": 2, "created": saved["created"], "note": "",
                                                       "angles": [-90.0, 90.0], "gap_min": 2, "gap_max": 2}
        assert c.get(f"{api}/patterns/nope").status_code == 404
        c.post(f"{api}/connect", json={"port": "sim"}); c.post(f"{api}/vicon/connect", json={"host": "sim"})
        b = {k: v for k, v in pblock([]).items() if k != "pattern_items"}
        body = {"subject": {"mass_kg": 30, "mode": "running", "baseline_n": 7}, "blocks": [{**b, "pattern": "nope"}]}
        assert "not found" in c.post(f"{api}/study", json=body).json()["error"]["message"]
        body["blocks"] = [{**b, "pattern": "lat-2", "n_perturbations": 2, "trigger_side": "any"}]
        assert c.post(f"{api}/study", json=body).status_code == 200
        assert c.get(f"{api}/study/protocol").json()["blocks"][0]["pattern_items"][1] == {"angle_deg": 90.0, "gap_steps": 2}
        c.patch(f"{api}/params", json={"fmax_n": 100}); c.post(f"{api}/arm")
        end = time.monotonic() + 4
        while c.get(f"{api}/status").json()["state"] != "ARMED" and time.monotonic() < end:
            time.sleep(0.05)
        c.post(f"{api}/study/gait", json={"duration_s": 5})
        end = time.monotonic() + 8
        while c.get(f"{api}/study").json()["state"] == "gait" and time.monotonic() < end:
            time.sleep(0.2)
        c.post(f"{api}/log/start")
        r = c.post(f"{api}/study/start")
        assert r.status_code == 409 and "baseline 5 N, the protocol wants 7 N" in r.json()["error"]["message"]
        c.patch(f"{api}/params", json={"baseline_n": 7})
        assert c.post(f"{api}/study/start").json()["state"] == "running"
        end = time.monotonic() + 5
        while c.get(f"{api}/study").json()["state"] == "running" and time.monotonic() < end:
            time.sleep(0.2)
        s = c.get(f"{api}/study").json()
        assert s["state"] == "finished" and s["done"] == 2, s
        time.sleep(1.2)                                                       # the last pulse runs to its end
        c.post(f"{api}/estop")
        if c.get(f"{api}/log").json()["recording"]:
            done = c.post(f"{api}/log/stop").json()
            rep = c.get(f"{api}/log/delay").json()                            # D51: the study pulls, measured
            assert [p["pulse_id"] for p in rep["pulses"]] and rep["recommended_latency_ms"] is not None
            assert all(p.get("timing_error_ms") is not None and p.get("command_ms") is not None for p in rep["pulses"]), rep["text"]
            assert Path(rep["file"]).is_file() and "recommended System delay" in rep["text"]


def test_error_log(tmp_path):
    """D51: API problems, page errors and board events land in errors_<day>.jsonl."""
    import json
    from fastapi.testclient import TestClient
    from bumpem.server import create_app
    with TestClient(create_app(log_dir=str(tmp_path))) as c:
        api = "/api/v1"
        assert c.post(f"{api}/arm").status_code == 409                       # no board
        c.post(f"{api}/errors", json={"page": "BumpemActivation.html", "message": "TypeError: x is null", "stack": "at f"})
        c.post(f"{api}/connect", json={"port": "sim"})
        c.post(f"{api}/estop")
        end = time.monotonic() + 2
        while not any(e["message"].startswith("STATE ESTOP") for e in c.get(f"{api}/errors").json()) and time.monotonic() < end:
            time.sleep(0.05)
        recent = c.get(f"{api}/errors").json()
        kinds = {(e["source"], e["level"]) for e in recent}
        assert ("api", "warn") in kinds and ("client", "error") in kinds and ("board", "warn") in kinds
        assert any(e.get("request") == "POST /api/v1/arm" and e["status"] == 409 for e in recent)
        lines = [json.loads(x) for x in c.get(f"{api}/errors/file").text.splitlines()]
        assert len(lines) == len(recent) and lines[1]["page"] == "BumpemActivation.html"
        assert c.get(f"{api}/errors/file?day=20000101").status_code == 404


def test_delay_report_perturbations(tmp_path):
    """D51: plain perturbations on the simulator: command, rise, lag, ratio measured; no study → no System delay."""
    from fastapi.testclient import TestClient
    from bumpem.server import create_app
    with TestClient(create_app(log_dir=str(tmp_path))) as c:
        api = "/api/v1"
        c.post(f"{api}/connect", json={"port": "sim"}); c.patch(f"{api}/params", json={"arm_ms": 0, "kff": 2})
        c.post(f"{api}/arm")
        end = time.monotonic() + 3
        while c.get(f"{api}/status").json()["state"] != "ARMED" and time.monotonic() < end:
            time.sleep(0.05)
        c.post(f"{api}/log/start", json={"label": "delays"})
        time.sleep(0.5)
        for a in (90, -90):
            assert c.post(f"{api}/perturbation", json={"angle_deg": a, "amplitude_n": 20, "phase1_ms": 50, "dur_ms": 400,
                                                       "phase2_ms": 50, "delay_ms": 30}).status_code == 200
            time.sleep(0.8)
        assert c.get(f"{api}/log/delay").status_code == 409                    # still recording
        c.post(f"{api}/log/stop")
        rep = c.get(f"{api}/log/delay").json()
        assert len(rep["pulses"]) == 2 and rep["recommended_latency_ms"] is None
        for p in rep["pulses"]:
            assert p["module"] in ("A", "C") and p["command_ms"] is not None and -5 < p["command_ms"] < 60
            assert p["rise_ms"] is not None and p["ratio"] is not None
        assert "No study pulls" in c.get(f"{api}/log/delay?format=text").text
        c.post(f"{api}/estop")

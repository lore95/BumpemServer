"""ViconReader (SDK in its own process) against tests/fake_vicon_dssdk/ (same layout as the real vicon_dssdk package, SDK 1.13)."""
import threading
import time

import pytest

from bumpem.vicon import ViconReader

FAKE = "fake_vicon_dssdk"                     # package laid out like vicon_dssdk


def wait(cond, s=5.0):
    end = time.monotonic() + s
    while not cond() and time.monotonic() < end:
        time.sleep(0.01)
    return cond()


def test_reader_streams_fz_per_subsample():
    frames, ended = [], threading.Event()
    r = ViconReader("127.0.0.1:801", lambda f, s: frames.append((f, s)), lambda m: ended.set(), sdk=FAKE)
    assert r.plates == ["Left Plate", "Right Plate"] and r.rate_hz == 100
    r.start()
    assert wait(lambda: len(frames) > 5)
    r.close()
    assert len({f for f, _ in frames}) == len(frames)                           # every frame once
    f, subs = frames[0]
    assert len(subs) == 10 and subs[0] == {"Left Plate": 700.0, "Right Plate": 0.0}   # Vicon -700 on the plate → GRF +700
    time.sleep(0.1)
    assert not ended.is_set() and not r._proc.is_alive()                        # closing is not a lost link


def test_reader_reports_lost_link():
    msg = []
    r = ViconReader("drop:801", lambda f, s: None, msg.append, sdk=FAKE)
    r.start()
    assert wait(lambda: msg) and "lost" in msg[0]
    r.close()


def test_reader_errors():
    with pytest.raises(ValueError, match="cannot connect"):
        ViconReader("bad:801", lambda f, s: None, lambda m: None, sdk=FAKE)
    with pytest.raises(ValueError, match="no force plate"):
        ViconReader("noplates:801", lambda f, s: None, lambda m: None, timeout_s=0.3, sdk=FAKE)
    with pytest.raises(TimeoutError):
        ViconReader("noframe:801", lambda f, s: None, lambda m: None, timeout_s=0.3, sdk=FAKE)
    with pytest.raises(ValueError, match="Vicon SDK not usable"):
        ViconReader("127.0.0.1:801", lambda f, s: None, lambda m: None, sdk="no_such_vicon_module")


def test_plate_names_fall_back_to_ids():
    r = ViconReader("nonames:801", lambda f, s: None, lambda m: None, sdk=FAKE)
    assert r.plates == ["Plate 1", "Plate 2"]
    r.close()


def _replay_file(folder, n_frames=30, subs=10, rate=100):
    """A tiny replay: plate Left = 100 × frame index, Right = sub index."""
    p = folder / "tiny.csv"
    with p.open("w") as f:
        f.write("t_s,frame,sub,Fz_Left,Fz_Right\n")
        for k in range(n_frames):
            for s in range(subs):
                f.write(f"{k / rate + s / (rate * subs):.4f},{k + 1},{s},{100.0 * k},{float(s)}\n")
    return p


def test_replay_plays_recorded_plates_and_loops(tmp_path):
    from bumpem.vicon import ReplayReader
    _replay_file(tmp_path)
    frames = []
    r = ReplayReader("tiny", lambda f, s: frames.append((f, s)), lambda m: None, folder=tmp_path)
    assert r.plates == ["Left", "Right"] and r.rate_hz == 100 and r.host == "replay:tiny"
    r.start()
    assert wait(lambda: len(frames) > 35)                                        # 30 frames, then from the start again
    r.close()
    assert [f for f, _ in frames[:35]] == list(range(1, 36))                     # frame numbers keep counting
    assert frames[0][1][3] == {"Left": 0.0, "Right": 3.0} and len(frames[0][1]) == 10
    assert frames[30][1][0]["Left"] == 0.0 and frames[29][1][0]["Left"] == 2900.0   # looped


def test_replay_names_and_missing_files(tmp_path):
    from bumpem.vicon import ReplayReader
    for bad in ("../x", ".hidden", "a/b"):
        with pytest.raises(ValueError):
            ReplayReader(bad, lambda f, s: None, lambda m: None, folder=tmp_path)
    with pytest.raises(ValueError, match="no replay"):
        ReplayReader("nothing", lambda f, s: None, lambda m: None, folder=tmp_path)


def test_server_connects_a_replay(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    import bumpem.vicon as V
    from bumpem.server import create_app
    _replay_file(tmp_path)
    monkeypatch.setattr(V, "REPLAY_DIR", tmp_path)
    with TestClient(create_app()) as c:
        v = c.post("/api/v1/vicon/connect", json={"host": "replay:tiny"}).json()
        assert v["connected"] and v["plates"] == ["Left", "Right"] and v["host"] == "replay:tiny"
        assert c.post("/api/v1/vicon/connect", json={"host": "replay:nothing"}).status_code == 422
        assert c.post("/api/v1/vicon/connect", json={"host": "replay:../x"}).status_code == 422

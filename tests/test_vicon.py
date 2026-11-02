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

"""ViconReader against a fake `vicon_dssdk` that follows SDK 1.13's ViconDataStream.py (GetFrame False = no frame)."""
import sys
import threading
import time
import types
from enum import Enum

import pytest

from bumpem.vicon import ViconReader


class DataStreamException(Exception):
    pass


class FakeClient:
    class StreamMode:
        EServerPush = 2

    plates = {"Left Plate": [-700.0] * 10, "Right Plate": [0.0] * 10}

    def __init__(self):
        self.connected, self.frame, self.calls, self.mode = False, 0, 0, None

    def Connect(self, host):
        if host.startswith("bad"):
            raise DataStreamException("CouldNotConnect")
        self.connected = True

    def IsConnected(self):
        return self.connected

    def Disconnect(self):
        self.connected = False

    def EnableDeviceData(self):
        pass

    def SetStreamMode(self, mode):
        self.mode = mode

    def GetFrame(self):
        if not self.connected:
            raise DataStreamException("NotConnected")
        self.calls += 1
        if self.calls % 3 == 0:          # no new frame now and then
            return False
        self.frame += 1
        time.sleep(0.001)
        return True

    def GetFrameNumber(self):
        return self.frame

    def GetFrameRate(self):
        return 100.0

    class DeviceType(Enum):
        EUnknownDevice = 0
        EForceplate = 1

    def GetDeviceNames(self):
        if self.frame < 3:                    # device data arrive a few frames after EnableDeviceData
            return []
        F = FakeClient.DeviceType.EForceplate
        return [("Left Plate", F), ("EMG", FakeClient.DeviceType.EUnknownDevice), ("Right Plate", F)]

    def GetForcePlates(self):
        return [] if self.frame < 3 else [1, 2]

    def GetGlobalForceVector(self, plate_id):
        name = ["Left Plate", "Right Plate"][plate_id - 1]
        return [(1.0, 2.0, fz) for fz in self.plates[name]]


@pytest.fixture
def sdk(monkeypatch):
    mod = types.SimpleNamespace(DataStreamException=DataStreamException, Client=FakeClient)
    pkg = types.ModuleType("vicon_dssdk")
    pkg.ViconDataStream = mod
    monkeypatch.setitem(sys.modules, "vicon_dssdk", pkg)
    return mod


def test_reader_streams_fz_per_subsample(sdk):
    frames, ended = [], threading.Event()
    r = ViconReader("127.0.0.1:801", lambda f, s: frames.append((f, s)), lambda m: ended.set())
    assert r.plates == ["Left Plate", "Right Plate"] and r.rate_hz == 100 and r._client.mode == 2
    r.start()
    end = time.monotonic() + 2
    while len(frames) < 6 and time.monotonic() < end:
        time.sleep(0.01)
    r.close()
    assert len(frames) > 5 and len({f for f, _ in frames}) == len(frames)      # every frame once
    f, subs = frames[0]
    assert len(subs) == 10 and subs[0] == {"Left Plate": -700.0, "Right Plate": 0.0}
    assert not ended.is_set()                                                   # closing is not a lost link


def test_reader_reports_lost_link(sdk):
    msg = []
    r = ViconReader("127.0.0.1:801", lambda f, s: None, msg.append)
    r.start()
    time.sleep(0.02)
    r._client.connected = False
    end = time.monotonic() + 2
    while not msg and time.monotonic() < end:
        time.sleep(0.01)
    assert msg and "lost" in msg[0]


def test_reader_errors(sdk, monkeypatch):
    with pytest.raises(ValueError, match="cannot connect"):
        ViconReader("bad:801", lambda f, s: None, lambda m: None)
    monkeypatch.setattr(FakeClient, "GetForcePlates", lambda self: [])
    with pytest.raises(ValueError, match="no force plate"):
        ViconReader("127.0.0.1:801", lambda f, s: None, lambda m: None, timeout_s=0.2)
    monkeypatch.setattr(FakeClient, "GetFrame", lambda self: False)
    with pytest.raises(TimeoutError):
        ViconReader("127.0.0.1:801", lambda f, s: None, lambda m: None, timeout_s=0.1)


def test_plate_names_fall_back_to_ids(sdk, monkeypatch):
    monkeypatch.setattr(FakeClient, "GetDeviceNames", lambda self: [])
    r = ViconReader("127.0.0.1:801", lambda f, s: None, lambda m: None)
    assert r.plates == ["Plate 1", "Plate 2"]


def test_reader_without_sdk(monkeypatch):
    monkeypatch.setitem(sys.modules, "vicon_dssdk", None)                       # import fails
    with pytest.raises(ValueError, match="Vicon SDK not usable"):
        ViconReader("127.0.0.1:801", lambda f, s: None, lambda m: None)

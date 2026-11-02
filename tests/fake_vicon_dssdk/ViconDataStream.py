"""Stand-in for `vicon_dssdk/ViconDataStream.py` (SDK 1.13), same layout as the real package: an empty package
`__init__.py` and this submodule with `Client` and `DataStreamException` at module level. Importable by the reader process.
The host name picks the behaviour: "bad…" refuses, "drop…" loses the link after 20 frames, "noplates…", "noframe…",
"nonames…" (no device names), "gil…" (GetFrame waits 10 ms holding the GIL, like the real _CoreClient3.pyd)."""
import ctypes
import time
from enum import Enum


class DataStreamException(Exception):
    pass


class Client:
    class StreamMode:
        EServerPush = 2

    class DeviceType(Enum):
        EUnknownDevice = 0
        EForceplate = 1

    def __init__(self):
        self.connected, self.frame, self.calls, self.host = False, 0, 0, ""

    def GetVersion(self):
        return (1, 13, 0)

    def Connect(self, host):
        if host.startswith("bad"):
            raise DataStreamException("CouldNotConnect")
        self.connected, self.host = True, host

    def IsConnected(self):
        return self.connected

    def Disconnect(self):
        self.connected = False

    def EnableDeviceData(self):
        pass

    def SetStreamMode(self, mode):
        pass

    def GetFrame(self):
        if not self.connected:
            raise DataStreamException("NotConnected")
        if self.host.startswith("noframe"):
            return False
        if self.host.startswith("gil"):
            ctypes.PyDLL(None).usleep(10000)     # PyDLL keeps the GIL during the call, as Vicon's module does
        self.calls += 1
        if self.calls % 3 == 0:                  # no new frame now and then
            return False
        self.frame += 1
        if self.host.startswith("drop") and self.frame > 20:
            self.connected = False
            raise DataStreamException("NotConnected")
        time.sleep(0.002)
        return True

    def GetFrameNumber(self):
        return self.frame

    def GetFrameRate(self):
        return 100.0

    def GetDeviceNames(self):
        if self.frame < 3 or self.host.startswith("nonames"):   # device data arrive a few frames after enabling
            return []
        F, U = Client.DeviceType.EForceplate, Client.DeviceType.EUnknownDevice
        return [("Left Plate", F), ("EMG", U), ("Right Plate", F)]

    def GetDeviceOutputDetails(self, name):
        return [("Force", c, "N") for c in ("Fx", "Fy", "Fz")]

    def GetForcePlates(self):
        return [] if self.frame < 3 or self.host.startswith("noplates") else [1, 2]

    def GetGlobalForceVector(self, plate_id):
        return [(1.0, 2.0, -700.0 if plate_id == 1 else 0.0)] * 10


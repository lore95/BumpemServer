"""Vicon DataStream check, read-only, force plates only (no markers, D31): connect, print frame rate, devices with their
outputs, then a few seconds of Fz per force plate so you can see which plate is the left belt (stand on one belt).

  python scripts/vicon_probe.py                         # host from the legacy MATLAB script
  python scripts/vicon_probe.py --host 192.168.10.1:801 --seconds 10

Before: Nexus open in Live mode on the Vicon PC (DataStream is served on port 801 while it runs).
Needs the Vicon DataStream SDK Python package `vicon_dssdk` (bundle wheel, D36). Calls checked against SDK 1.13.
Force plate Fz: forces on the plate in plate axes (Z up): standing reads negative. Untested against the lab system.
"""
from __future__ import annotations

import argparse
import sys
import time

try:
    from vicon_dssdk import ViconDataStream
except ImportError as e:
    sys.exit(f"Vicon SDK not usable ({e}): run update.bat from a bundle that carries vicon_dssdk")


def next_frame(client) -> None:
    while True:          # GetFrame: False = no frame yet (SDK 1.13), exception = other errors
        try:
            if client.GetFrame():
                return
        except ViconDataStream.DataStreamException:
            pass
        time.sleep(0.001)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host", default="192.168.10.1:801", help="Vicon PC address:port (legacy/MATLAB_script.m:3)")
    ap.add_argument("--seconds", type=float, default=5.0, help="how long to print Fz")
    a = ap.parse_args()

    client = ViconDataStream.Client()
    print("connecting to", a.host)
    client.Connect(a.host)
    client.EnableDeviceData()
    client.SetAxisMapping(ViconDataStream.Client.AxisMapping.EForward, ViconDataStream.Client.AxisMapping.ELeft,
                          ViconDataStream.Client.AxisMapping.EUp)
    next_frame(client)
    print(f"frame {client.GetFrameNumber()}, {client.GetFrameRate():.0f} Hz")

    end = time.time() + 5                     # device data join the stream some frames after enabling
    while not client.GetDeviceNames() and time.time() < end:
        next_frame(client)
    plates = []
    for name, kind in client.GetDeviceNames():
        print(f"device {name!r} ({kind})")
        for output, component, unit in client.GetDeviceOutputDetails(name):
            print(f"    {output} / {component} [{unit}]")
            if component == "Fz":
                plates.append((name, output, component))
    if not plates:
        sys.exit("no device output with component Fz: check that the force plates are enabled in Nexus")

    print("\nFz per plate (mean over the frame's subsamples). Stand on one belt to see which one is left.")
    t_end = time.time() + a.seconds
    while time.time() < t_end:
        next_frame(client)
        cols = []
        for name, output, component in plates:
            values, _ = client.GetDeviceOutputValues(name, output, component)
            cols.append(f"{name}: {sum(values) / max(len(values), 1):8.1f} N")
        print("   ".join(cols))
        time.sleep(0.2)
    client.Disconnect()


if __name__ == "__main__":
    main()

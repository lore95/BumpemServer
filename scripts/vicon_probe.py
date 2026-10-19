"""Vicon DataStream check, read-only: connect, print frame rate, devices (force plates) with their outputs, subjects,
then a few seconds of Fz per force plate so you can see which plate is the left belt (stand on one belt).

  python scripts/vicon_probe.py                         # host from the legacy MATLAB script
  python scripts/vicon_probe.py --host 192.168.10.1:801 --seconds 10

Before: Nexus open in Live mode on the Vicon PC (DataStream is served on port 801 while it runs).
Needs the Vicon DataStream SDK Python package `vicon_dssdk` (installed from the SDK folder, docs/knowledge/gait_detection.md).
Untested against the lab system: written from the SDK's Python API.
"""
from __future__ import annotations

import argparse
import sys
import time

try:
    from vicon_dssdk import ViconDataStream
except ImportError:
    sys.exit("vicon_dssdk missing: install the Vicon DataStream SDK, then pip install its Python folder")


def next_frame(client) -> None:
    while True:
        try:
            client.GetFrame()
            return
        except ViconDataStream.DataStreamException:
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
    client.EnableMarkerData()
    client.EnableSegmentData()
    client.SetAxisMapping(ViconDataStream.Client.AxisMapping.EForward, ViconDataStream.Client.AxisMapping.ELeft,
                          ViconDataStream.Client.AxisMapping.EUp)
    next_frame(client)
    print(f"frame {client.GetFrameNumber()}, {client.GetFrameRate():.0f} Hz")

    plates = []
    for name, kind in client.GetDeviceNames():
        print(f"device {name!r} ({kind})")
        for output, component, unit in client.GetDeviceOutputDetails(name):
            print(f"    {output} / {component} [{unit}]")
            if component == "Fz":
                plates.append((name, output, component))
    for subject in client.GetSubjectNames():
        print(f"subject {subject!r}: {len(client.GetMarkerNames(subject))} markers")
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

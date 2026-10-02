"""Vicon DataStream client — NOT IMPLEMENTED.

Target behavior (legacy/MATLAB_script.m:20-41, 71-84):
- connect to host "192.168.10.1:801", EnableDeviceData, ClientPull, axis Forward/Left/Up
- per frame, per force-plate subsample: Fz_total = Fz(plate 0) + Fz(plate 1)
- yield (t_s, frame, sub_idx, fz_total)

Needs: Vicon DataStream SDK Python bindings (ship with the SDK installer). Check the version on the lab PC.
"""


def stream(host: str = "192.168.10.1:801"):
    raise NotImplementedError("Vicon client pending — see module docstring and docs/STATUS.md")

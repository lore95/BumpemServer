"""Test print: three small plates with a slot key of different clearance and one M6 hole each.
Slide each into a tower slot, bolt on with the existing T-nut: the one that slides in without play sets KEY_CLEAR.
Run: python test_fit.py  ->  out/test_fit.stl, out/test_fit.step"""
from pathlib import Path

import cadquery as cq

import tower as P

L, W = 30.0, 24.0                       # plate length (along the slot) and width
CLEARANCES = (0.1, 0.2, 0.3)            # per side


def coupon(clear: float, marks: int) -> cq.Workplane:
    plate = cq.Workplane("XY").box(L, W, P.PLATE_T, centered=(True, True, False))
    key = cq.Workplane("XY").box(L, P.SLOT_OPEN - 2 * clear, P.KEY_H, centered=(True, True, False)).translate((0, 0, -P.KEY_H))
    part = plate.union(key).faces(">Z").workplane().hole(P.BOLT_HOLE)
    for i in range(marks):              # 1, 2 or 3 notches on one edge = clearance 0.1 / 0.2 / 0.3
        part = part.cut(cq.Workplane("XY").box(1.5, 2.0, P.PLATE_T + 1).translate((-L / 2 + 4 + 3 * i, W / 2, P.PLATE_T / 2)))
    return part


def build() -> cq.Workplane:
    parts = [coupon(c, i + 1).translate((0, i * (W + 6), 0)) for i, c in enumerate(CLEARANCES)]
    out = parts[0]
    for p in parts[1:]:
        out = out.union(p)
    return out.rotate((0, 0, 0), (1, 0, 0), 180).translate((0, 0, P.PLATE_T))  # flat top on the bed, key up: no overhangs


if __name__ == "__main__":
    d = Path(__file__).parent / "out"
    d.mkdir(exist_ok=True)
    part = build()
    cq.exporters.export(part, str(d / "test_fit.stl"))
    cq.exporters.export(part, str(d / "test_fit.step"))
    print("written", d / "test_fit.stl")

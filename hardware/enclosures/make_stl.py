"""Export the ready parts as STL + STEP in print orientation.  Run: python make_stl.py  ->  out/<name>.stl
Plates with a key and a rail/ledge on opposite faces print standing on their end (cross-section on the bed): no supports; use a brim."""
from pathlib import Path

import cadquery as cq

import parts


def on_end(wp: cq.Workplane) -> cq.Workplane:
    """Stand the part on its -x end: the slot direction becomes vertical."""
    w = wp.rotate((0, 0, 0), (0, 1, 0), -90)
    bb = w.val().BoundingBox()
    return w.translate((-bb.center.x, -bb.center.y, -bb.zmin))


def on_side(wp: cq.Workplane) -> cq.Workplane:
    """Lay the part on its -y side (holes and keys horizontal)."""
    w = wp.rotate((0, 0, 0), (1, 0, 0), -90)
    bb = w.val().BoundingBox()
    return w.translate((-bb.center.x, -bb.center.y, -bb.zmin))


def rsp_pair() -> cq.Workplane:
    a, b = on_side(parts.rsp_bracket("A")), on_side(parts.rsp_bracket("B"))
    bb = a.val().BoundingBox()
    return a.union(b.translate((0, bb.ylen + 10, 0)))


READY = {
    "rsp2000_brackets": rsp_pair,
    "iaa100_din_mount": lambda: on_end(parts.din_rail_mount()),
    "rs15_plate": lambda: on_end(parts.rs15_holder()),
}

if __name__ == "__main__":
    d = Path(__file__).parent / "out"
    d.mkdir(exist_ok=True)
    for name, build in READY.items():
        wp = build()
        cq.exporters.export(wp, str(d / f"{name}.stl"))
        cq.exporters.export(wp, str(d / f"{name}.step"))
        bb = wp.val().BoundingBox()
        print(f"{name}: {bb.xlen:.0f} x {bb.ylen:.0f} x {bb.zlen:.0f} mm (bed x, y, height)")

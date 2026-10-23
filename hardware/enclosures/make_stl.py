"""Export the ready parts as STL + STEP in print orientation.  Run: python make_stl.py  ->  out/<name>.stl
Every part prints flat, key side down (the key on the bed keeps it accurate): supports from the build plate under the plate wings
(2.5 mm, against the profile face, so a rough finish there is fine), the 48 V pad ledges and the DIN rail flanges. Standing on end (up to 107 mm, small footprint) toppled halfway
on the makerspace printer (2026-10-19)."""
from pathlib import Path

import cadquery as cq

import parts


def flat(wp: cq.Workplane) -> cq.Workplane:
    """As modelled: back face down, key on the bed."""
    bb = wp.val().BoundingBox()
    return wp.translate((-bb.center.x, -bb.center.y, -bb.zmin))


def rsp_pair() -> cq.Workplane:
    a, b = flat(parts.rsp_bracket("A")), flat(parts.rsp_bracket("B"))
    bb = a.val().BoundingBox()
    return a.union(b.translate((0, bb.ylen + 10, 0)))


READY = {
    "rsp2000_brackets": rsp_pair,
    "rsp2000_bracket_B": lambda: flat(parts.rsp_bracket("B")),   # fan end alone: fit_check has only A (2026-10-22)
    "iaa100_din_mount": lambda: flat(parts.din_rail_mount()),
    "rs15_plate": lambda: flat(parts.rs15_holder()),
    "ground_bar_mount": lambda: flat(parts.ground_bar_mount()),
    "carrier_plate": lambda: flat(parts.carrier_plate()),                 # once: the tower with the carrier board (2026-10-23)
}

# Beds laid out like fit_check.stl: (name, part, rotate 90 deg, centre x, y)
_GND = lambda: flat(parts.ground_bar_mount())
BEDS = {
    "tower_set": [                                           # one tower's set; print it 4 times (2026-10-22)
        ("rsp2000_bracket_A", lambda: flat(parts.rsp_bracket("A")), False, 41, 58.5),
        ("rsp2000_bracket_B", lambda: flat(parts.rsp_bracket("B")), False, 125, 58.5),
        ("iaa100_din_mount", lambda: flat(parts.din_rail_mount()), True, 190, 55),
        ("rs15_plate", lambda: flat(parts.rs15_holder()), False, 75, 145.5)],
    "second_print": [                                        # once: carrier board plate + 4 ground bar plates (2026-10-23)
        ("carrier_plate", lambda: flat(parts.carrier_plate()), False, 125, 48)]
        + [(f"ground_bar_mount_{i + 1}", _GND, False, x, y) for i, (x, y) in enumerate([(64.5, 116), (189.5, 116), (64.5, 156), (189.5, 156)])],
}
BED = (250, 210)


def bed(name: str) -> cq.Workplane:
    """One print bed, centred like the other STLs; a part past the bed or < 4 mm from another raises."""
    out, boxes = None, []
    for part, build, rot, cx, cy in BEDS[name]:
        wp = build()
        if rot:
            wp = wp.rotate((0, 0, 0), (0, 0, 1), 90)
        wp = wp.translate((cx, cy, 0))
        bb = wp.val().BoundingBox()
        assert 0 <= bb.xmin and bb.xmax <= BED[0] and 0 <= bb.ymin and bb.ymax <= BED[1], f"{part} off the bed"
        for o in boxes:
            assert bb.xmax + 4 <= o.xmin or o.xmax + 4 <= bb.xmin or bb.ymax + 4 <= o.ymin or o.ymax + 4 <= bb.ymin, f"{part} too close"
        boxes.append(bb)
        out = wp if out is None else out.union(wp)
    return flat(out)


if __name__ == "__main__":
    d = Path(__file__).parent / "out"
    d.mkdir(exist_ok=True)
    for name, build in READY.items():
        wp = build()
        cq.exporters.export(wp, str(d / f"{name}.stl"))
        cq.exporters.export(wp, str(d / f"{name}.step"))
        bb = wp.val().BoundingBox()
        print(f"{name}: {bb.xlen:.0f} x {bb.ylen:.0f} x {bb.zlen:.0f} mm (bed x, y, height)")
    for name in BEDS:
        wp = bed(name)
        cq.exporters.export(wp, str(d / f"{name}.stl"))
        bb = wp.val().BoundingBox()
        print(f"{name}.stl: {len(wp.solids().vals())} parts, {bb.xlen:.0f} x {bb.ylen:.0f} x {bb.zlen:.0f} mm")

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
}

# The whole print job, one STL per bed like fit_check.stl: (bed, name, part, rotate 90 deg, centre x, y). 14 parts need
# ~93,000 mm2, more than one bed, so 3 beds of 250 x 210 mm (Prusa MK4 / Core One; Bambu 256 x 256 too) (2026-10-22).
_A, _B = (lambda: flat(parts.rsp_bracket("A"))), (lambda: flat(parts.rsp_bracket("B")))
_IAA, _RS15 = (lambda: flat(parts.din_rail_mount())), (lambda: flat(parts.rs15_holder()))
ALL = [(1, f"rs15_plate_{i + 1}", _RS15, True, 39.5 + 57 * i, 68.75) for i in range(4)] + [
    (1, "iaa100_din_mount_1", _IAA, False, 70, 165), (1, "iaa100_din_mount_2", _IAA, False, 180, 165),
] + [(2, f"rsp2000_bracket_A_{i + 1}", _A, True, 68.5, 36 + 67 * i) for i in range(3)] + [
    (2, f"rsp2000_bracket_B_{i + 1}", _B, True, 181.5, 46 + 87 * i) for i in range(2)] + [
    (3, "rsp2000_bracket_B_3", _B, False, 61, 73.5), (3, "rsp2000_bracket_B_4", _B, False, 151, 73.5),
    (3, "iaa100_din_mount_3", _IAA, False, 70, 165)]
BED = (250, 210)


def print_bed(n: int) -> cq.Workplane:
    """Bed n of the print job, centred like the other STLs; a part past the bed or < 4 mm from another raises."""
    out, boxes = None, []
    for bed, name, build, rot, cx, cy in ALL:
        if bed != n:
            continue
        wp = build()
        if rot:
            wp = wp.rotate((0, 0, 0), (0, 0, 1), 90)
        wp = wp.translate((cx, cy, 0))
        bb = wp.val().BoundingBox()
        assert 0 <= bb.xmin and bb.xmax <= BED[0] and 0 <= bb.ymin and bb.ymax <= BED[1], f"{name} off the bed"
        for o in boxes:
            assert bb.xmax + 4 <= o.xmin or o.xmax + 4 <= bb.xmin or bb.ymax + 4 <= o.ymin or o.ymax + 4 <= bb.ymin, f"{name} too close"
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
    for n in (1, 2, 3):
        wp = print_bed(n)
        cq.exporters.export(wp, str(d / f"print_bed_{n}.stl"))
        bb = wp.val().BoundingBox()
        print(f"print_bed_{n}.stl: {len(wp.solids().vals())} parts, {bb.xlen:.0f} x {bb.ylen:.0f} x {bb.zlen:.0f} mm")

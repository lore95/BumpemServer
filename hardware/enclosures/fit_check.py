"""One print with one of each: slot test plate (clearance 0.2 mm, 2 notches), IAA100 DIN-rail mount, RS-15-24 plate, RSP-2000 bracket A,
laid out on one bed; plus a 3-page PDF of these parts.  Run: python fit_check.py  ->  out/fit_check.stl, out/fit_check.pdf"""
from pathlib import Path

import cadquery as cq
from matplotlib.backends.backend_pdf import PdfPages

import make_stl
import overview
import parts
import test_fit
import tower as P

GAP = 12.0


def test_plate() -> cq.Workplane:
    return test_fit.coupon(0.2, 2).rotate((0, 0, 0), (1, 0, 0), 180).translate((0, 0, P.PLATE_T))   # flat top on the bed


def layout() -> cq.Workplane:
    """Two rows of two, so the bed stays well under 256 x 256 mm."""
    rows = [[make_stl.flat(parts.din_rail_mount()), make_stl.flat(parts.rsp_bracket("A"))],
            [make_stl.flat(parts.rs15_holder()), test_plate()]]
    out, y = None, 0.0
    for row in rows:
        x, h = 0.0, 0.0
        for wp in row:
            bb = wp.val().BoundingBox()
            wp = wp.translate((x - bb.xmin, y - bb.ymin, 0))
            out = wp if out is None else out.union(wp)
            x += bb.xlen + GAP
            h = max(h, bb.ylen)
        y += h + GAP
    return out


PAGES = [
    ("Slot test plate", test_fit.coupon(0.2, 2), "READY TO PRINT",
     "One test plate, key 9.6 mm (clearance 0.2 mm per side, 2 notches). Slides into the slot and bolts on with one M6 + T-nut: checks key fit, hole and bolt length.",
     "nothing"),
    ("IAA100 DIN-rail mount", parts.din_rail_mount(), "READY (datasheet)", None, None),
    ("24 V supply plate (RS-15-24)", parts.rs15_holder(), "READY (datasheet)", None, None),
    ("48 V supply brackets (RSP-2000-48)", parts.rsp_bracket("A"), "READY (datasheet)", None, None),
]

if __name__ == "__main__":
    d = Path(__file__).parent / "out"
    wp = layout()
    cq.exporters.export(wp, str(d / "fit_check.stl"))
    bb = wp.val().BoundingBox()
    print(f"fit_check.stl: bed {bb.xlen:.0f} x {bb.ylen:.0f} mm, height {bb.zlen:.0f} mm")
    with PdfPages(d / "fit_check.pdf") as pdf:
        for name, part, status, what, needed in PAGES:
            if what is None:
                _, status, what, needed = parts.PARTS[name]
            overview.page(pdf, name, part, status, what, needed)
    print("written", d / "fit_check.pdf")

"""Export the ready parts as STL + STEP in print orientation.  Run: python make_stl.py  ->  out/<name>.stl
Every part prints flat, key side down (the key on the bed keeps it accurate): supports from the build plate under the plate wings
(2.5 mm, against the profile face, so a rough finish there is fine), the 48 V pad ledges and the DIN rail flanges. Standing on end (up to 107 mm, small footprint) toppled halfway
on the makerspace printer (2026-10-19)."""
import zipfile
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

# The whole print job in one file: (group, name, part, rotate 90 deg, centre x, y). 14 parts need ~93,000 mm2, more than one bed,
# so 3 groups of 250 x 210 mm (Prusa MK4 / Core One; Bambu 256 x 256 too), side by side 300 mm apart: group 1 sits on
# the bed, Bambu / Orca "Arrange" spreads the rest onto plates. 3MF keeps every part a separate object (2026-10-22).
_A, _B = (lambda: flat(parts.rsp_bracket("A"))), (lambda: flat(parts.rsp_bracket("B")))
_IAA, _RS15 = (lambda: flat(parts.din_rail_mount())), (lambda: flat(parts.rs15_holder()))
ALL = [(1, f"rs15_plate_{i + 1}", _RS15, True, 39.5 + 57 * i, 68.75) for i in range(4)] + [
    (1, "iaa100_din_mount_1", _IAA, False, 70, 165), (1, "iaa100_din_mount_2", _IAA, False, 180, 165),
] + [(2, f"rsp2000_bracket_A_{i + 1}", _A, True, 68.5, 36 + 67 * i) for i in range(3)] + [
    (2, f"rsp2000_bracket_B_{i + 1}", _B, True, 181.5, 46 + 87 * i) for i in range(2)] + [
    (3, "rsp2000_bracket_B_3", _B, False, 61, 73.5), (3, "rsp2000_bracket_B_4", _B, False, 151, 73.5),
    (3, "iaa100_din_mount_3", _IAA, False, 70, 165)]
BED = (250, 210)


def all_parts_3mf(path: Path) -> None:
    """Every part as its own named object; overlaps or a group past the bed raise."""
    objs, boxes = [], []
    for group, name, build, rot, cx, cy in ALL:
        wp = build()
        if rot:
            wp = wp.rotate((0, 0, 0), (0, 0, 1), 90)
        wp = wp.translate((cx + 300 * (group - 1), cy, 0))
        bb = wp.val().BoundingBox()
        x0 = bb.xmin - 300 * (group - 1)
        assert 0 <= x0 and x0 + bb.xlen <= BED[0] and 0 <= bb.ymin and bb.ymax <= BED[1], f"{name} off the bed"
        for b in boxes:
            assert bb.xmax + 4 <= b.xmin or b.xmax + 4 <= bb.xmin or bb.ymax + 4 <= b.ymin or b.ymax + 4 <= bb.ymin, f"{name} too close"
        boxes.append(bb)
        verts, tris = wp.val().tessellate(1e-3, 0.1)
        keys = [f'x="{p.x:.4f}" y="{p.y:.4f}" z="{p.z:.4f}"' for p in verts]   # faces repeat their edge vertices: weld them
        idx = {k: i for i, k in enumerate(dict.fromkeys(keys))}
        v = "".join(f"<vertex {k}/>" for k in idx)
        t = "".join(f'<triangle v1="{idx[keys[a]]}" v2="{idx[keys[b]]}" v3="{idx[keys[c]]}"/>' for a, b, c in tris
                    if len({keys[a], keys[b], keys[c]}) == 3)
        objs.append((name, f"<mesh><vertices>{v}</vertices><triangles>{t}</triangles></mesh>"))
    model = ('<?xml version="1.0" encoding="UTF-8"?>\n<model unit="millimeter" xml:lang="en-US" '
             'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"><resources>'
             + "".join(f'<object id="{i + 1}" name="{n}" type="model">{m}</object>' for i, (n, m) in enumerate(objs))
             + "</resources><build>" + "".join(f'<item objectid="{i + 1}"/>' for i in range(len(objs))) + "</build></model>")
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", '<?xml version="1.0" encoding="UTF-8"?>\n<Types xmlns="http://schemas.openxmlformats.org/'
                   'package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.'
                   'relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel'
                   '+xml"/></Types>')
        z.writestr("_rels/.rels", '<?xml version="1.0" encoding="UTF-8"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/'
                   'package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/'
                   '3dmanufacturing/2013/01/3dmodel"/></Relationships>')
        z.writestr("3D/3dmodel.model", model)
    print(f"{path.name}: {len(objs)} parts in 3 groups of {BED[0]} x {BED[1]} mm")


if __name__ == "__main__":
    d = Path(__file__).parent / "out"
    d.mkdir(exist_ok=True)
    for name, build in READY.items():
        wp = build()
        cq.exporters.export(wp, str(d / f"{name}.stl"))
        cq.exporters.export(wp, str(d / f"{name}.step"))
        bb = wp.val().BoundingBox()
        print(f"{name}: {bb.xlen:.0f} x {bb.ylen:.0f} x {bb.zlen:.0f} mm (bed x, y, height)")
    all_parts_3mf(d / "all_parts.3mf")

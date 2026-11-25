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


def front_down(wp: cq.Workplane) -> cq.Workplane:
    """Covers: flipped, front wall on the bed, walls and ears straight up (no supports)."""
    return flat(wp.rotate((0, 0, 0), (1, 0, 0), 180))


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
    "psu48_cover_1": lambda: front_down(parts.rsp_cover(1)),              # supply covers (2026-11-24): front wall on the bed
    "psu48_cover_2": lambda: front_down(parts.rsp_cover(2)),
    "psu24_cover": lambda: front_down(parts.rs15_cover()),
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


COVERS = ["psu48_cover_1", "psu48_cover_2", "psu24_cover"]   # one tower's covers; too big for one bed together (2026-11-25)


def write_3mf(path: Path, names: list[str]) -> None:
    """One 3MF with each part as its own named object, side by side: the slicer arranges them onto as many plates as it needs."""
    import zipfile
    objs, items, x = [], [], 0.0
    for i, name in enumerate(names, 1):
        shape = READY[name]().val()
        verts, tris = shape.tessellate(0.02, 0.1)
        bb = shape.BoundingBox()
        ids, pts = {}, []                                    # weld: faces are tessellated apart, slicers want one closed mesh
        for p in verts:
            k = (round(p.x, 3), round(p.y, 3), round(p.z, 3))
            if k not in ids:
                ids[k] = len(pts); pts.append(k)
        remap = [ids[(round(p.x, 3), round(p.y, 3), round(p.z, 3))] for p in verts]
        v = "".join(f'<vertex x="{x:.3f}" y="{y:.3f}" z="{z:.3f}"/>' for x, y, z in pts)
        t = "".join(f'<triangle v1="{remap[a]}" v2="{remap[b]}" v3="{remap[c]}"/>' for a, b, c in tris)
        objs.append(f'<object id="{i}" name="{name}" type="model"><mesh><vertices>{v}</vertices><triangles>{t}</triangles></mesh></object>')
        items.append(f'<item objectid="{i}" transform="1 0 0 0 1 0 0 0 1 {x - bb.xmin:.3f} 0 0"/>')
        x += bb.xlen + 10
    model = ('<?xml version="1.0" encoding="UTF-8"?><model unit="millimeter" xml:lang="en-US" '
             'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
             f'<resources>{"".join(objs)}</resources><build>{"".join(items)}</build></model>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                   '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
        z.writestr("_rels/.rels", '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
        z.writestr("3D/3dmodel.model", model)


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
    write_3mf(d / "psu_covers.3mf", COVERS)
    print(f"psu_covers.3mf: {', '.join(COVERS)}")

"""PDF overview of the printed parts: one page per part with an isometric render, status and what is still needed.
Run: python overview.py  ->  out/parts-overview.pdf"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np

import parts
import test_fit
import render
import tower as P

COLORS = {"READY TO PRINT": "#1f8a5b", "READY (geometry)": "#1f8a5b", "READY (datasheet)": "#1f8a5b", "CONCEPT": "#c77d12"}
TMP = Path(__file__).parent / "out" / "renders"


def images(name, wp, status):
    """PNG of the part alone and, if available, mounted on the profile with the device envelope."""
    TMP.mkdir(parents=True, exist_ok=True)
    col = (0.55, 0.66, 0.80) if status != "CONCEPT" else (0.90, 0.72, 0.45)
    alone = TMP / f"{name}.png"
    render.render_png([(wp, col, 1.0)], alone)
    ctx = parts.CONTEXT.get(name)
    if not ctx:
        return alone, None
    length, slots, devices = ctx
    prof = parts.profile_block(length, slots)
    if name.startswith("48 V"):
        prof = prof.translate((parts.RSP["L"] / 2, 0, 0))
    items = [(wp, col, 1.0), (prof, parts.GREY, 1.0)] + [((d[0]() if isinstance(d, tuple) else d()), *(d[1:] if isinstance(d, tuple) else (parts.AMBER, 0.55))) for d in devices]
    mounted = TMP / f"{name} mounted.png"
    render.render_png(items, mounted)
    return alone, mounted


def page(pdf, title, wp, status, what, needed):
    import textwrap
    fig = plt.figure(figsize=(8.27, 11.69))
    fig.text(0.07, 0.955, title, fontsize=17, weight="bold")
    fig.text(0.07, 0.935, status, fontsize=10, weight="bold", color=COLORS[status])
    alone, mounted = images(title, wp, status)
    bb = wp.val().BoundingBox()
    if mounted:
        for rect, img, cap in (([0.03, 0.66, 0.46, 0.26], alone, "Part"), ([0.51, 0.66, 0.46, 0.26], mounted, "On the profile (grey), device in red")):
            ax = fig.add_axes(rect); ax.imshow(plt.imread(img)); ax.set_axis_off(); ax.set_title(cap, fontsize=8, color="#555")
    else:
        ax = fig.add_axes([0.15, 0.66, 0.7, 0.26]); ax.imshow(plt.imread(alone)); ax.set_axis_off()
    y = 0.635

    def para(head, body, size=9.5, width=100):
        nonlocal y
        fig.text(0.07, y, head, fontsize=10.5, weight="bold"); y -= 0.02
        for w in textwrap.wrap(body, width):
            fig.text(0.07, y, w, fontsize=size); y -= 0.016
        y -= 0.01

    guide = parts.GUIDE.get(title)
    para("Role", guide[0] if guide else what)
    if guide:
        fig.text(0.07, y, "How to anchor it", fontsize=10.5, weight="bold"); y -= 0.02
        for n, step in enumerate(guide[1], 1):
            lines = textwrap.wrap(step, 92)
            fig.text(0.07, y, f"{n}.", fontsize=9.5)
            for w in lines:
                fig.text(0.095, y, w, fontsize=9.5); y -= 0.016
            y -= 0.004
        y -= 0.008
    para("Data", f"Size {bb.xlen:.0f} x {bb.ylen:.0f} x {bb.zlen:.0f} mm. Mount: {P.BOLT} button-head bolts in slot-{P.SLOT_OPEN:.0f} T-nuts, "
         f"key {parts.KEY_W:.1f} mm in the slot. Still needed: {needed}.", size=9)
    if status == "CONCEPT":
        para("Note", "Concept only: device sizes are placeholders, the final part will change.", size=9)
    pdf.savefig(fig); plt.close(fig)


def cover(pdf):
    fig = plt.figure(figsize=(8.27, 11.69))
    fig.text(0.07, 0.94, "Bump'em tower: printed parts", fontsize=20, weight="bold")
    info = [f"Profile: 90x90 light, B-type (Bosch-compatible), slot {P.SLOT_OPEN:.0f}, 2 slots per face {P.SLOT_PITCH:.0f} mm apart",
            f"Fasteners: {P.BOLT} ISO 7380 button head (4 mm hex) + existing slot-10 T-nuts; plates {P.PLATE_T:.0f} mm thick",
            "Material: PETG or ASA (not PLA: softens near warm drivers / supplies). Print flat, key side down; supports from the build plate under the plate wings.",
            "Device sizes: Futek IAA100 drawing FI1573, Mean Well RS-15 case 971A (docs/reference/).",
            "48 V supply RSP-2000-48 (295x127x41 mm, 1.95 kg, case 952D): 2 printed end brackets, 10 mm air gap, ASA preferred.",
            "Source: BumpemServer/hardware/enclosures (CadQuery). Dimensions in tower.py."]
    for i, t in enumerate(info):
        fig.text(0.07, 0.89 - i * 0.025, t, fontsize=10)
    fig.text(0.07, 0.72, "Part", weight="bold"); fig.text(0.45, 0.72, "Status", weight="bold"); fig.text(0.65, 0.72, "Still needed", weight="bold")
    for i, (name, (_, status, _, needed)) in enumerate(parts.PARTS.items()):
        y = 0.69 - i * 0.05
        fig.text(0.07, y, name, fontsize=10)
        fig.text(0.45, y, status, fontsize=10, color=COLORS[status], weight="bold")
        import textwrap
        for j, w in enumerate(textwrap.wrap(needed, 34)):
            fig.text(0.65, y - j * 0.015, w, fontsize=8.5)
    fig.text(0.07, 0.27, "Order: 1) print the slot test plates, 2) report which fits, 3) measure the devices marked\n"
             "PLACEHOLDER, 4) final holders are generated from those numbers.", fontsize=10)
    fig.text(0.07, 0.22, "Mains: the power strip is only carried by printed hooks; no 230 V parts inside printed housings.", fontsize=10)
    pdf.savefig(fig); plt.close(fig)


if __name__ == "__main__":
    out = Path(__file__).parent / "out" / "parts-overview.pdf"
    with PdfPages(out) as pdf:
        cover(pdf)
        for name, (build, status, what, needed) in parts.PARTS.items():
            wp = test_fit.build() if build is None else build()
            page(pdf, name, wp, status, what, needed)
    print("written", out)

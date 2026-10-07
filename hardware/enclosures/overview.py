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
    items = [(wp, col, 1.0), (parts.profile_block(length, slots), parts.GREY, 1.0)] + [(d(), parts.AMBER, 0.55) for d in devices]
    mounted = TMP / f"{name} mounted.png"
    render.render_png(items, mounted)
    return alone, mounted


def page(pdf, title, wp, status, what, needed):
    fig = plt.figure(figsize=(8.27, 11.69))
    fig.text(0.07, 0.95, title, fontsize=18, weight="bold")
    fig.text(0.07, 0.925, status, fontsize=11, weight="bold", color=COLORS[status])
    alone, mounted = images(title, wp, status)
    bb = wp.val().BoundingBox(); size = (bb.xlen, bb.ylen, bb.zlen)
    boxes = [([0.05, 0.56, 0.9, 0.34], alone, "Part (as modelled; print orientation in the STL)")]
    if mounted:
        boxes.append(([0.05, 0.27, 0.9, 0.29], mounted, "Mounted on the profile (grey); device envelope in red"))
    else:
        boxes[0] = ([0.05, 0.30, 0.9, 0.58], alone, boxes[0][2])
    for rect, img, cap in boxes:
        ax = fig.add_axes(rect); ax.imshow(plt.imread(img)); ax.set_axis_off(); ax.set_title(cap, fontsize=9, color="#555")
    lines = [f"What: {what}", f"Size: {size[0]:.0f} x {size[1]:.0f} x {size[2]:.0f} mm",
             f"Mount: {P.BOLT} button-head screws in slot-{P.SLOT_OPEN:.0f} T-nuts; key {parts.KEY_W:.1f} mm in the slot",
             f"Still needed: {needed}"]
    if status == "CONCEPT":
        lines.append("Concept only: device sizes are placeholders, the final part will change.")
    import textwrap
    y = 0.23
    for ln in lines:
        for w in textwrap.wrap(ln, 95):
            fig.text(0.07, y, w, fontsize=10); y -= 0.02
        y -= 0.008
    pdf.savefig(fig); plt.close(fig)


def cover(pdf):
    fig = plt.figure(figsize=(8.27, 11.69))
    fig.text(0.07, 0.94, "Bump'em tower: printed parts", fontsize=20, weight="bold")
    info = [f"Profile: 90x90 light, B-type (Bosch-compatible), slot {P.SLOT_OPEN:.0f}, 2 slots per face {P.SLOT_PITCH:.0f} mm apart",
            f"Fasteners: {P.BOLT} ISO 7380 button head (4 mm hex) + existing slot-10 T-nuts; plates {P.PLATE_T:.0f} mm thick",
            "Material: PETG or ASA (not PLA: softens near warm drivers / supplies). No supports needed.",
            "Device sizes: Futek IAA100 drawing FI1573, Mean Well RS-15 case 971A (docs/reference/).",
            "Not printed: 48 V supply RSP-2000-48 (295x127x41 mm, 1.95 kg, 3x M4, needs airflow): metal brackets.",
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

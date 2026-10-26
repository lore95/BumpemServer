"""Soldering guide for the carrier board: top (parts) and bottom (solder) views drawn from the board data, plus steps.
Run:  $KPY dump_board.py bumpem-carrier.kicad_pcb fab/board.json  then  python soldering_guide.py  ->  fab/bumpem-carrier-soldering.pdf"""
import json
import math
import textwrap
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Circle, FancyArrowPatch, Rectangle

HERE = Path(__file__).parent
D = json.loads((HERE / "fab/board.json").read_text())
W, H = 154.0, 96.0
A4 = (8.27, 11.69)
TOP, BOT, PART, MARK, COPPER = "#d9534f", "#3a6fb0", "#f2c14e", "#c2185b", "#b87333"
FP = {f["ref"]: f for f in D["fps"]}
KIND = {"U": "socket", "R": "resistor", "D": "diode", "J": "plug", "H": "hole"}


def seg_dist(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L))
    return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)


def on_layer(x, y, net, layer):
    return any(s["layer"] == layer and s["net"] == net and seg_dist((x, y), s["a"], s["b"]) < 0.3 for s in D["segs"])


# pads reached only by a top-layer track, and signal vias: both need solder on the top if the holes are not plated
TOP_PADS = [(f["ref"], p) for f in D["fps"] for p in f["pads"]
            if p["net"] and p["net"] != "GND" and on_layer(p["x"], p["y"], p["net"], "F.Cu") and not on_layer(p["x"], p["y"], p["net"], "B.Cu")]
SIG_VIAS = [s for s in D["segs"] if s["layer"] == "via" and s["net"] != "GND"]


def text(fig, x, y, s, width=100, size=9.5, gap=0.016, **kw):
    for line in textwrap.wrap(s, width):
        fig.text(x, y, line, fontsize=size, **kw)
        y -= gap
    return y


def steps(fig, x, y, items, width=92, size=9.5):
    for n, s in enumerate(items, 1):
        fig.text(x, y, f"{n}.", fontsize=size, weight="bold")
        y = text(fig, x + 0.03, y, s, width, size) - 0.006
    return y


def board(ax, side):
    """side 'top': seen from the parts side. 'bottom': seen from the solder side (mirrored left-right)."""
    X = (lambda x: x) if side == "top" else (lambda x: W - x)
    ax.set_aspect("equal"); ax.set_axis_off()
    ax.add_patch(Rectangle((0, 0), W, H, facecolor="#f4efe6", edgecolor="#333", lw=1.2))
    for s in D["segs"]:
        if s["layer"] in ("F.Cu", "B.Cu"):
            mine = (s["layer"] == "F.Cu") == (side == "top")
            ax.plot([X(s["a"][0]), X(s["b"][0])], [s["a"][1], s["b"][1]], color=TOP if s["layer"] == "F.Cu" else BOT,
                    lw=1.6 if mine else 0.8, alpha=0.9 if mine else 0.25, solid_capstyle="round", zorder=2)
    for s in D["segs"]:
        if s["layer"] == "via":
            gnd = s["net"] == "GND"                            # ground stitching: small and light, nothing to do there
            ax.add_patch(Circle((X(s["a"][0]), s["a"][1]), 0.45 if gnd else 0.7, color="#bbb" if gnd else "#222", zorder=3))
    for f in D["fps"]:
        bx, by, bw, bh = f["bbox"]
        if f["ref"].startswith("H"):
            ax.add_patch(Circle((X(f["x"]), f["y"]), 1.6, facecolor="white", edgecolor="#333", lw=1, zorder=4))
            ax.text(X(f["x"]), f["y"] + 3.6, "M3", ha="center", va="top", fontsize=5.5, color="#333")
            continue
        if side == "top":
            ax.add_patch(Rectangle((X(bx) if side == "top" else X(bx + bw), by), bw, bh, facecolor=PART, alpha=0.35,
                                   edgecolor="#8a6d00", lw=0.6, zorder=1))
        for p in f["pads"]:
            ax.add_patch(Circle((X(p["x"]), p["y"]), 0.85 if p["drill"] < 1.2 else 1.2, facecolor=COPPER, edgecolor="#5a3a12", lw=0.3, zorder=5))
            ax.add_patch(Circle((X(p["x"]), p["y"]), p["drill"] / 2 * 0.8, color="white", zorder=6))
    for ref, p in TOP_PADS:
        ax.add_patch(Circle((X(p["x"]), p["y"]), 2.1, fill=False, edgecolor=MARK, lw=1.4, zorder=7))
    for s in SIG_VIAS:
        ax.add_patch(Circle((X(s["a"][0]), s["a"][1]), 1.8, fill=False, edgecolor=MARK, lw=1.0, ls=(0, (2, 1)), zorder=7))
    # labels
    for f in D["fps"]:
        if f["ref"].startswith("H"):
            continue
        bx, by, bw, bh = f["bbox"]
        cx = X(bx + bw / 2)
        if f["ref"] == "U1":
            ax.text(cx, by + bh / 2, "U1  Teensy 4.1 socket\n2 x 24 female", ha="center", va="center", fontsize=7, weight="bold", zorder=8)
        elif f["ref"] == "U2":
            ax.text(cx, by + bh / 2, "U2  DAC socket\n2 x 6 female", ha="center", va="center", fontsize=6.5, weight="bold", zorder=8)
        elif f["ref"].startswith("J"):
            ax.text(cx, f["y"] + 3.2, f"{f['ref']}  {f['value']}", ha="center", va="top", fontsize=6.5, weight="bold", zorder=8)
        else:
            ax.text(X(f["x"]) + (1.9 if side == "top" else -1.9), f["y"] + 5, f["ref"], ha="left" if side == "top" else "right",
                    va="center", fontsize=5.5, weight="bold", rotation=90, zorder=8)
    for ref in ("D1", "D2", "D3", "D4"):                     # band = cathode = pad 1 (+3V3), towards the Teensy edge
        p1 = next(p for p in FP[ref]["pads"] if p["num"] == "1")
        if side == "top":
            ax.add_patch(Rectangle((X(p1["x"]) - 1.3, p1["y"] + 1.6), 2.6, 1.0, color="#222", zorder=8))
    usb_x = X(0.0)
    ax.annotate("USB", (usb_x, 14), (usb_x + (-9 if side == "top" else 9), 14), fontsize=7, ha="center", va="center",
                arrowprops=dict(arrowstyle="->", lw=0.8))
    ax.text(W / 2, H + 3.5, "module plugs: this edge (cables plug in here)", ha="center", va="top", fontsize=7, color="#555")
    ax.set_xlim(-14, W + 14); ax.set_ylim(H + 8, -6)


def legend(fig, y, side):
    items = [(TOP if side == "top" else BOT, "-", f"{'top' if side == 'top' else 'bottom'} copper track (on this side)"),
             (BOT if side == "top" else TOP, "-", f"{'bottom' if side == 'top' else 'top'} track (other side, seen through)"),
             (COPPER, "o", "pad with hole (one pin each)"),
             ("#222", "o", "via: track changes side here (small grey dots: ground vias, nothing to do)"),
             (MARK, "O", "circled: needs solder ON TOP too, if the holes are not plated (page 5)")]
    if side == "top":
        items.insert(0, (PART, "s", "where the part body sits"))
    for i, (c, m, s) in enumerate(items):
        yy = y - 0.018 * i
        if m == "-":
            fig.add_artist(plt.Line2D([0.08, 0.11], [yy + 0.004] * 2, color=c, lw=2, transform=fig.transFigure))
        elif m == "s":
            fig.add_artist(Rectangle((0.08, yy - 0.002), 0.03, 0.011, color=c, alpha=0.5, transform=fig.transFigure))
        elif m == "o":
            fig.add_artist(Circle((0.095, yy + 0.004), 0.005, color=c, transform=fig.transFigure))
        else:
            fig.add_artist(Circle((0.095, yy + 0.004), 0.007, fill=False, edgecolor=c, lw=1.4, transform=fig.transFigure))
        fig.text(0.125, yy, s, fontsize=8.5)
    return y - 0.018 * len(items)


def page_intro(pdf):
    fig = plt.figure(figsize=A4)
    fig.text(0.07, 0.95, "Carrier board v1: soldering guide", fontsize=18, weight="bold")
    y = text(fig, 0.07, 0.925, "Board 154 x 96 mm, bare copper (no printing). Every part goes on the TOP; every pin is soldered on the "
             "BOTTOM. Page 2: what the parts look like. Pages 3 and 4: both sides of the board. Page 5: if the holes are not plated.", 100)
    y -= 0.012
    fig.text(0.07, y, "Which side is which", fontsize=11, weight="bold"); y -= 0.022
    y = steps(fig, 0.07, y, [
        "Lay the board so the row of 4 large 5-pin footprints (module plugs J1-J4) is along the edge nearest you.",
        "TOP (parts side): the long double row of 24 pads (Teensy socket) is at the LEFT, starting at the left edge; the short double "
        "row of 6 (DAC socket) is right of it, near the far edge. The 2 left mounting holes are lower (32 and 58 mm from the far edge) "
        "than the 2 right ones (10 and 45 mm).",
        "If the Teensy rows are at the right instead, you are looking at the BOTTOM (solder side).",
        "Check against page 3: the tracks you see on the top must match the red tracks there.",
    ])
    y -= 0.008
    fig.text(0.07, y, "Before you start", fontsize=11, weight="bold"); y -= 0.022
    y = steps(fig, 0.07, y, [
        "Look into a few holes. Copper-lined (shiny ring inside) = plated: solder on the bottom only. Bare fibreglass inside = "
        "NOT plated: also do page 5.",
        "The board takes FEMALE headers (sockets). The Teensy and the DAC keep their male pins and plug in from the top. Never "
        "solder male pins into the board, and never solder the Teensy or DAC to it.",
        "Multimeter in beep mode at hand. No Teensy, no DAC, no modules on the board while soldering.",
    ])
    y -= 0.008
    fig.text(0.07, y, "Parts and order (lowest first; what they look like: next page)", fontsize=11, weight="bold")
    y -= 0.024
    rows = [
        ("1", "R1-R4", "4 x 1 kOhm resistor", "either way round; holes 10 mm apart"),
        ("2", "R5-R8", "4 x 1 MOhm resistor", "either way round; holes 7.6 mm apart"),
        ("3", "D1-D4", "4 x BAT85 diode (glass)", "BAND towards the far edge (Teensy side): page 3"),
        ("4", "U1", "2 x female header 1x24, 8.5 mm", "Teensy socket, two rows"),
        ("5", "U2", "2 x female header 1x6", "DAC socket, two rows"),
        ("6", "J1-J4", "4 x Phoenix MSTB 2,5/5-GF-5,08", "plug opening towards the board edge"),
    ]
    xs = [0.07, 0.11, 0.21, 0.52]
    for x, h in zip(xs, ["#", "Where", "Part", "How"]):
        fig.text(x, y, h, fontsize=9, weight="bold")
    y -= 0.006
    fig.add_artist(plt.Line2D([0.07, 0.93], [y, y], color="#999", lw=0.6, transform=fig.transFigure)); y -= 0.018
    for r in rows:
        for x, c in zip(xs, r):
            fig.text(x, y, c, fontsize=9)
        y -= 0.02
    pdf.savefig(fig); plt.close(fig)


BAND = {"black": "#111", "brown": "#7b4a1e", "red": "#d62728", "orange": "#ff7f0e", "yellow": "#f2d21b", "green": "#2ca02c",
        "gold": "#c9a227", "blue": "#1f5fbf"}


def draw_resistor(ax, x0, y0, bands, body):
    """Axial resistor, 6.3 x 2.5 mm body drawn 4:1."""
    s = 4
    ax.plot([x0 - 6 * s, x0 + 12.3 * s], [y0, y0], color="#999", lw=2, solid_capstyle="round")
    ax.add_patch(matplotlib.patches.FancyBboxPatch((x0, y0 - 1.25 * s), 6.3 * s, 2.5 * s, boxstyle="round,pad=0,rounding_size=4",
                                                   facecolor=body, edgecolor="#555", lw=0.8))
    for i, c in enumerate(bands):
        bx = x0 + (0.9 + 0.95 * i) * s if i < len(bands) - 1 else x0 + 5.1 * s
        ax.add_patch(Rectangle((bx, y0 - 1.25 * s), 0.45 * s, 2.5 * s, color=BAND[c]))


def page_parts(pdf):
    fig = plt.figure(figsize=A4)
    fig.text(0.07, 0.95, "What the parts look like", fontsize=18, weight="bold")
    text(fig, 0.07, 0.925, "Drawings, not to the same scale; real sizes in the text. German drawer labels in quotes. Bring this page "
         "and a multimeter: the resistor colours can be confusing, the meter is sure (1 kOhm reads 0.99-1.01 k, 1 MOhm 0.99-1.01 M).", 100)

    def panel(rect, title, lines):
        ax = fig.add_axes(rect); ax.set_aspect("equal"); ax.set_axis_off()
        fig.text(rect[0] + rect[2] + 0.01, rect[1] + rect[3] - 0.012, title, fontsize=10.5, weight="bold")
        yy = rect[1] + rect[3] - 0.032
        for l in lines:
            yy = text(fig, rect[0] + rect[2] + 0.01, yy, l, 52, 8.5, 0.0145) - 0.002
        return ax

    # 1 kOhm
    ax = panel([0.04, 0.76, 0.40, 0.12], "R1-R4: resistor 1 kOhm (x4)", [
        "\"Widerstand 1 k\" (1 kOhm, 1K0). Small cylinder, 6 mm long, 2.5 mm thick, a wire at each end.",
        "4 bands (beige body): brown-black-RED-gold.", "5 bands (blue body, 1 %): brown-black-black-BROWN-brown.",
        "0.25 W (any size this small is fine)."])
    draw_resistor(ax, 10, 12, ["brown", "black", "red", "gold"], "#e8d3a8")
    draw_resistor(ax, 10, -2, ["brown", "black", "black", "brown", "brown"], "#7fb3e0")
    ax.text(-26, 12, "4-band", fontsize=7, va="center"); ax.text(-26, -2, "5-band", fontsize=7, va="center")
    ax.set_xlim(-30, 62); ax.set_ylim(-10, 20)
    # 1 MOhm
    ax = panel([0.04, 0.61, 0.40, 0.12], "R5-R8: resistor 1 MOhm (x4)", [
        "\"Widerstand 1 M\" (1 MOhm, 1M0). Same size as the 1 k: only the colours differ.",
        "4 bands: brown-black-GREEN-gold.", "5 bands: brown-black-black-YELLOW-brown.",
        "Do not mix up with 1 k: the 3rd (4-band) or 4th (5-band) colour is the difference."])
    draw_resistor(ax, 10, 12, ["brown", "black", "green", "gold"], "#e8d3a8")
    draw_resistor(ax, 10, -2, ["brown", "black", "black", "yellow", "brown"], "#7fb3e0")
    ax.text(-26, 12, "4-band", fontsize=7, va="center"); ax.text(-26, -2, "5-band", fontsize=7, va="center")
    ax.set_xlim(-30, 62); ax.set_ylim(-10, 20)
    # BAT85
    ax = panel([0.04, 0.47, 0.40, 0.11], "D1-D4: diode BAT85 (x4)", [
        "\"Schottky-Diode BAT85\". Tiny glass body (3.8 mm long, 1.9 mm thick), orange-red and see-through, with a black "
        "band at one end = cathode. Printed text very small: use a magnifier.",
        "Substitutes if there is no BAT85: BAT43, BAT46, BAT42 (same job). NOT a 1N4148 (that is the wrong type)."])
    s = 4
    ax.plot([-20, 50], [0, 0], color="#999", lw=2)
    ax.add_patch(matplotlib.patches.FancyBboxPatch((5, -0.95 * s), 3.8 * s, 1.9 * s, boxstyle="round,pad=0,rounding_size=3.5",
                                                   facecolor="#e8774a", edgecolor="#a04020", lw=0.8, alpha=0.85))
    ax.add_patch(Rectangle((5 + 3.0 * s, -0.95 * s), 0.5 * s, 1.9 * s, color="#111"))
    ax.annotate("band = cathode\n(towards the far edge)", (5 + 3.25 * s, 0.95 * s), (36, 10), fontsize=7,
                arrowprops=dict(arrowstyle="-", lw=0.6))
    ax.set_xlim(-24, 62); ax.set_ylim(-8, 16)
    # female headers
    ax = panel([0.04, 0.29, 0.40, 0.15], "U1, U2: female headers (sockets)", [
        "\"Buchsenleiste 2,54 mm, 1-reihig\". Black plastic strip with a row of square holes on top, pins underneath. "
        "Need 2 x 24-pin (Teensy, 8.5 mm tall) and 2 x 6-pin (DAC).",
        "Longer strips (1 x 40) are fine: cut them with side cutters THROUGH the next hole (you lose one pin), file flat.",
        "NOT the \"Stiftleiste\" (male pin header: bare pins sticking up). Spare male strips only help hold the sockets "
        "straight while soldering."])
    n = 10
    ax.add_patch(Rectangle((0, 0), n * 2.54, 8.5, facecolor="#222", edgecolor="#000"))
    for i in range(n):
        ax.add_patch(Rectangle((0.7 + 2.54 * i, 7.4), 1.1, 1.0, color="#777"))
        ax.plot([1.27 + 2.54 * i] * 2, [0, -3.0], color="#c9a227", lw=1.6)
    ax.text(n * 2.54 + 1.5, 4, "...", fontsize=12, va="center")
    ax.text(0, 10.5, "side view: holes on top, pins below", fontsize=7)
    ax.add_patch(Rectangle((0, -9.5), n * 2.54, 2.5, facecolor="#222"))
    for i in range(n):
        ax.add_patch(Rectangle((0.8 + 2.54 * i, -8.9), 0.95, 1.2, color="#888"))
    ax.text(0, -12.5, "seen from the top", fontsize=7)
    ax.set_xlim(-2, 34); ax.set_ylim(-14, 13)
    # MSTB
    ax = panel([0.04, 0.08, 0.40, 0.18], "J1-J4: Phoenix MSTB header (x4) + plug (x4)", [
        "On the board: \"Leiterplatten-Grundleiste\" Phoenix MSTB 2,5/5-GF-5,08 (no. 1776537): green, 5 pin openings "
        "5.08 mm apart, a threaded hole in a flange at each end, 5 pins underneath. The opening faces sideways (horizontal).",
        "On each module cable: the plug MSTB 2,5/5-STF-5,08 (1778014): green, 5 screw terminals on top, wires in the side, "
        "a screw in each flange. Same family = they fit; other pitches (3.5 / 3.81 mm) do not.",
        "No Phoenix in the makerspace? Order them (README): no substitute keeps the locking flanges."])
    ax.add_patch(Rectangle((0, 0), 35.7, 9, facecolor="#3a8f3a", edgecolor="#1d5c1d"))
    for i in range(5):
        cx = 7.7 + 5.08 * i
        ax.add_patch(Rectangle((cx - 1.8, 2.0), 3.6, 5.0, facecolor="#1d4f1d"))
        ax.plot([cx, cx], [0, -3.5], color="#c9a227", lw=1.6)
    for fx in (2.3, 33.4):
        ax.add_patch(Circle((fx, 4.5), 1.3, facecolor="#c0c0c0", edgecolor="#555"))
    ax.text(0, 10.5, "board header, seen from the plug side", fontsize=7)
    ax.add_patch(Rectangle((0, -16), 35.7, 8, facecolor="#4aa04a", edgecolor="#1d5c1d"))
    for i in range(5):
        cx = 7.7 + 5.08 * i
        ax.add_patch(Circle((cx, -12), 1.6, facecolor="#c0c0c0", edgecolor="#555"))
        ax.plot([cx - 1.1, cx + 1.1], [-12, -12], color="#555", lw=0.8)
    for fx in (2.3, 33.4):
        ax.add_patch(Circle((fx, -12), 1.1, facecolor="#999", edgecolor="#555"))
    ax.text(0, -19, "cable plug, seen from above (5 wire screws)", fontsize=7)
    ax.set_xlim(-2, 38); ax.set_ylim(-21, 12)
    pdf.savefig(fig); plt.close(fig)


def page_side(pdf, side):
    fig = plt.figure(figsize=A4)
    if side == "top":
        fig.text(0.07, 0.95, "3. TOP side: where every part goes", fontsize=18, weight="bold")
        y = text(fig, 0.07, 0.925, "Seen from above, parts side up, module plugs at the bottom of the picture. Push each part in "
                 "from this side; its pins come out on the bottom.", 100)
    else:
        fig.text(0.07, 0.95, "4. BOTTOM side: where you solder", fontsize=18, weight="bold")
        y = text(fig, 0.07, 0.925, "The board turned over (left and right swap: the Teensy is now on the RIGHT). Every pad here gets "
                 "one solder joint: heat pad and pin together 2-3 s, feed solder until it forms a small cone, cut the leads ~1 mm.", 100)
    ax = fig.add_axes([0.03, 0.47, 0.94, 0.42])
    board(ax, side)
    y = legend(fig, 0.45, side) - 0.012
    if side == "top":
        steps(fig, 0.07, y, [
            "Resistors and diodes: bend the leads to the hole spacing, push them in until the body lies on the board, bend the "
            "leads out a little underneath so they stay, solder, cut.",
            "Diodes D1-D4: the black band (black bar in the picture) goes to the hole nearer the far edge (the 3.3 V line). Wrong "
            "way round, it shorts the force signal to 3.3 V.",
            "Sockets: plug the female headers onto the Teensy (and the DAC) or onto spare male pin strips, set them in, solder one "
            "pin at each end, check they sit flat and straight, then solder the rest.",
            "MSTB plugs J1-J4: the opening where the cable plug goes in faces the near board edge; the flange screws are at its ends.",
        ])
    else:
        steps(fig, 0.07, y, [
            "Small joints, no bridges: socket pins are only 2.54 mm apart. After each row, look at it against light.",
            "Ground pads sit in the copper fill and take longer to heat: hold the iron 1-2 s more.",
            "Circled pads and vias: if the holes are not plated, they also need the top-side work on page 5.",
        ])
    pdf.savefig(fig); plt.close(fig)


def page_unplated(pdf):
    fig = plt.figure(figsize=A4)
    fig.text(0.07, 0.95, "5. Only if the holes are NOT plated", fontsize=18, weight="bold")
    y = text(fig, 0.07, 0.925, "In a plated board the copper inside each hole joins the top and bottom. Without it, a joint on the "
             "bottom does not reach a top track. Two places need extra work (circled in pink on pages 3 and 4):", 100)
    y -= 0.012
    fig.text(0.07, y, f"A. {len(TOP_PADS)} pads with a track only on the TOP: solder them on the top as well", fontsize=11, weight="bold")
    y -= 0.024
    for ref, p in TOP_PADS:
        what = {"U1": "Teensy socket, Teensy pin 19", "U2": "DAC socket, its SCL pin"}.get(ref, "diode, band end")
        fig.text(0.09, y, f"{ref} pad {p['num']}  ({what}): {p['net']}", fontsize=9.5); y -= 0.018
    y -= 0.006
    y = text(fig, 0.07, y, "Diodes D1-D4: the band-end lead is reachable next to the body: solder it on the top as well as underneath "
             "(the top track joins the 4 diodes to 3.3 V). SCL (U1 pad 41 = Teensy pin 19, far row, 8th from the left; U2 pad 3 = "
             "DAC far row, 3rd from the left): the top track runs only between these two pins and the socket plastic covers it. "
             "Easiest: ignore that track and solder a short insulated wire on the BOTTOM from the one pin to the other.", 100)
    y = text(fig, 0.07, y, "Ground needs nothing: every ground pin reaches the bottom copper fill, which is one piece (checked on "
             "the board file, 2026-10-26).", 100)
    y -= 0.016
    fig.text(0.07, y, f"B. {len(SIG_VIAS)} signal vias: a short wire through each, soldered on both sides", fontsize=11, weight="bold")
    y -= 0.022
    y = text(fig, 0.07, y, "A via is where a track goes from one side to the other. Do them right after the resistors and diodes (no via sits under "
             "a part), before the sockets: push a cut-off resistor or diode lead (or thin solid wire, max 0.7 mm) through, solder "
             "on top and bottom, cut both ends short. The 12 parts give exactly 24 offcuts; keep them. Grey vias (ground): leave them.", 100)
    y -= 0.008
    nets = {}
    for s in SIG_VIAS:
        nets.setdefault(s["net"], []).append(s["a"])
    for n, pts in sorted(nets.items()):
        fig.text(0.09, y, f"{n}: " + ",  ".join(f"({p[0]:.0f}, {p[1]:.0f}) mm" for p in pts), fontsize=9); y -= 0.017
    y -= 0.006
    text(fig, 0.07, y, "Positions in mm from the top-left corner seen from the top (USB edge left, plug edge at the bottom). "
         "Check each with the multimeter afterwards: beep from the pad on one side to the track it should reach on the other.", 100, 8.5)
    pdf.savefig(fig); plt.close(fig)


def page_check(pdf):
    fig = plt.figure(figsize=A4)
    fig.text(0.07, 0.95, "6. Check before plugging anything in", fontsize=18, weight="bold")
    y = text(fig, 0.07, 0.925, "Multimeter on beep. No Teensy, no DAC, no modules (README 'Assembly and first power-up').", 100)
    y -= 0.01
    steps(fig, 0.07, y, [
        "3V3 to GND must NOT beep: Teensy socket 3V3 pin to any J pin 3 or 4.",
        "Each plug J1-J4: pins 3 and 4 to a Teensy socket GND pin must beep.",
        "J1 pin 1 to Teensy socket pin 27 must beep; J2 pin 1 to 28, J3 to 29, J4 to 30 (module enable).",
        "DAC socket SCL to Teensy pin 19 and SDA to pin 18 must beep (these use the top track and a via: page 5).",
        "Each J pin 2 (setpoint) to its DAC output pin must beep (A-D: through vias).",
        "Then plug in the DAC and the Teensy (USB at the board edge), USB only: bumpem info --port <PORT> must answer.",
        "One module at a time, 48 V off: plug in, then scripts/open_loop_test.sh for that module.",
    ])
    pdf.savefig(fig); plt.close(fig)


if __name__ == "__main__":
    out = HERE / "fab/bumpem-carrier-soldering.pdf"
    with PdfPages(out) as pdf:
        page_intro(pdf)
        page_parts(pdf)
        page_side(pdf, "top")
        page_side(pdf, "bottom")
        page_unplated(pdf)
        page_check(pdf)
    print("written", out, f"({len(TOP_PADS)} top-only pads, {len(SIG_VIAS)} signal vias)")

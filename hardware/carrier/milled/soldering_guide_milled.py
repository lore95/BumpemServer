"""Soldering guide for the makerspace (single-sided) carrier board, drawn from fab/board.json (build_milled.sh writes it).
Run: python soldering_guide_milled.py  ->  fab/bumpem-carrier-milled-soldering.pdf"""
import json
import textwrap
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Circle, Rectangle

HERE = Path(__file__).parent
D = json.loads((HERE / "fab/board.json").read_text())
W, H = 154.0, 96.0
A4 = (8.27, 11.69)
COPPER, PART, OK, WIRE, TRK = "#b87333", "#f2c14e", "#1a9e4a", "#e07b00", "#3a6fb0"
FP = {f["ref"]: f for f in D["fps"]}
LINKS = sorted((r for r in FP if r.startswith("W")), key=lambda r: int(r[1:]))


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


def pads(*refs):
    return [(p["x"], p["y"]) for r in refs for p in FP[r]["pads"] if p["net"]]


def board(ax, side, refs, marks=(), title="", all_links=False):
    X = (lambda x: x) if side == "top" else (lambda x: W - x)
    ax.set_aspect("equal"); ax.set_axis_off()
    ax.add_patch(Rectangle((0, 0), W, H, facecolor="#f4efe6", edgecolor="#333", lw=1.2))
    if side == "bottom":
        for s in D["segs"]:
            if s["layer"] == "B.Cu":
                ax.plot([X(s["a"][0]), X(s["b"][0])], [s["a"][1], s["b"][1]], color=TRK, lw=0.9, alpha=0.35, zorder=2)
    for f in D["fps"]:
        if f["ref"].startswith("W"):
            continue
        mine = f["ref"] in refs
        if f["ref"].startswith("H"):
            ax.add_patch(Circle((X(f["x"]), f["y"]), 1.6, facecolor="white", edgecolor="#999", lw=0.8, zorder=4)); continue
        if mine and side == "top":
            bx, by, bw, bh = f["bbox"]
            ax.add_patch(Rectangle((X(bx), by), bw, bh, facecolor=PART, alpha=0.6, edgecolor="#8a6d00", lw=0.8, zorder=1))
        for p in f["pads"]:
            cu = bool(p["net"])
            ax.add_patch(Circle((X(p["x"]), p["y"]), (0.95 if p["drill"] < 1.2 else 1.25) if cu else 0.5,
                                facecolor=(COPPER if mine else "#ddd") if cu else "white", edgecolor="#5a3a12" if mine else "#bbb",
                                lw=0.3, zorder=5))
        if mine and not f["ref"].startswith("U"):
            bx, by, bw, bh = f["bbox"]
            ax.text(X(bx + bw / 2), by - 0.8 if not f["ref"].startswith("J") else f["y"] + 3.2, f["ref"], fontsize=6.5,
                    weight="bold", ha="center", va="bottom" if not f["ref"].startswith("J") else "top", zorder=9)
    for r in LINKS:
        if r in refs or all_links:
            (a, b) = FP[r]["pads"]
            ax.plot([X(a["x"]), X(b["x"])], [a["y"], b["y"]], color=WIRE, lw=2.4, zorder=8, solid_capstyle="round",
                    alpha=1.0 if side == "top" else 0.5)
            for p in (a, b):
                ax.add_patch(Circle((X(p["x"]), p["y"]), 0.95, facecolor=COPPER, edgecolor="#5a3a12", lw=0.3, zorder=8))
            if side == "top":
                ax.text(X((a["x"] + b["x"]) / 2) + 1.2, (a["y"] + b["y"]) / 2, r, fontsize=6.5, weight="bold", color=WIRE, zorder=9)
    for x, y in marks:
        ax.add_patch(Circle((X(x), y), 2.0, fill=False, edgecolor=OK, lw=1.6, zorder=10))
    for r, lbl in (("U1", "Teensy socket"), ("U2", "DAC socket")):
        bx, by, bw, bh = FP[r]["bbox"]
        ax.text(X(bx + bw / 2), by + bh / 2, lbl, ha="center", va="center", fontsize=6.5, zorder=9,
                color="#333" if r in refs else "#aaa", weight="bold" if r in refs else "normal")
    ax.annotate("USB", (X(0.0), 14), (X(0.0) + (-9 if side == "top" else 9), 14), fontsize=7, ha="center", va="center",
                arrowprops=dict(arrowstyle="->", lw=0.8))
    ax.text(W / 2, H + 3.5, "plug edge: towards you", ha="center", va="top", fontsize=7, color="#555")
    ax.set_title(title, fontsize=10, weight="bold", loc="left")
    ax.set_xlim(-14, W + 14); ax.set_ylim(H + 8, -4)


def page_step(pdf, n, title, what, refs, todo, top_marks=(), all_links=False):
    fig = plt.figure(figsize=A4)
    fig.text(0.07, 0.955, f"Step {n}: {title}", fontsize=17, weight="bold")
    text(fig, 0.07, 0.932, what, 100)
    board(fig.add_axes([0.05, 0.60, 0.90, 0.27]), "top", refs, top_marks, "TOP (parts side): the part goes in here", all_links)
    board(fig.add_axes([0.05, 0.31, 0.90, 0.27]), "bottom", refs,
          [p for p in pads(*refs)], "BOTTOM (copper side, turned over): green rings = solder here", all_links)
    steps(fig, 0.07, 0.285, todo)
    pdf.savefig(fig); plt.close(fig)


def page_intro(pdf):
    fig = plt.figure(figsize=A4)
    fig.text(0.07, 0.95, "Carrier board, makerspace version: soldering guide", fontsize=16, weight="bold")
    y = text(fig, 0.07, 0.925, "Single-sided board: all copper is on the BOTTOM, every joint is soldered there, nothing on the top. "
             "Around each pad there is bare board, so solder that misses the pad does not stick: flick it off. 70 joints in total.", 100)
    y -= 0.01
    fig.text(0.07, y, "What is different from the first board", fontsize=11, weight="bold"); y -= 0.022
    y = steps(fig, 0.07, y, [
        "Unused socket pins have a bare hole, no copper: the header still goes in whole, those pins are simply not soldered "
        "(VIN can no longer touch anything).",
        "7 wire links (W1-W7): short insulated wires on the top side, soldered underneath like a resistor. They replace the "
        "vias and the top-side SCL track of the first board.",
        "The 1 kOhm resistors also bridge over tracks (their bodies are the bridge). R2 has a longer leg spacing (15 mm).",
        "The 1 MOhm resistors connect each force input to its own module's enable line (not to 3.3 V): armed, a loose force "
        "cable reads ~200 N and the board goes to FAULT, as on the first board (D23). No diodes.",
        "No labels printed: the module letters A-D are milled into the copper next to each plug, on the bottom.",
    ])
    y -= 0.008
    fig.text(0.07, y, "Parts (lowest first)", fontsize=11, weight="bold"); y -= 0.024
    rows = [("1", "W1-W7", "insulated wire, 0.5 mm core, ~2-5 cm each", "14"),
            ("2", "R1-R4", "4 x 1 kOhm (drawer 1 K)", "8"),
            ("3", "R5-R8", "4 x 1 MOhm (drawer 1 M)", "8"),
            ("4", "U1", "2 x female header 1x24 (Teensy)", "12"),
            ("5", "U2", "2 x female header 1x6 (DAC)", "8"),
            ("6", "J1-J4", "4 x Phoenix MSTB 2,5/5-GF-5,08", "20")]
    for x, h in zip([0.07, 0.11, 0.21, 0.80], ["#", "Where", "Part", "Joints"]):
        fig.text(x, y, h, fontsize=9, weight="bold")
    y -= 0.006
    fig.add_artist(plt.Line2D([0.07, 0.93], [y, y], color="#999", lw=0.6, transform=fig.transFigure)); y -= 0.018
    for r in rows:
        for x, c in zip([0.07, 0.11, 0.21, 0.80], r):
            fig.text(x, y, c, fontsize=9)
        y -= 0.02
    y -= 0.01
    text(fig, 0.07, y, "Which side is which: the copper tracks are on the bottom. Lay the board copper side down, plug edge "
         "towards you: the Teensy socket is at the top LEFT, the DAC socket right of it. Turned over (copper up), the "
         "Teensy is at the top RIGHT and the letters A-D read correctly.", 100)
    pdf.savefig(fig); plt.close(fig)


def page_check(pdf):
    fig = plt.figure(figsize=A4)
    fig.text(0.07, 0.95, "Step 7: check before plugging anything in", fontsize=17, weight="bold")
    y = text(fig, 0.07, 0.925, "Multimeter on beep, nothing plugged in. Then the Teensy and DAC, USB only.", 100) - 0.01
    steps(fig, 0.07, y, [
        "Each wire link: beep from the pad at one end to the track at the other end (W1-W7).",
        "3V3 to GND must NOT beep: Teensy socket 3V3 pin to any plug pin 3 or 4.",
        "Each plug: pins 3 and 4 to the Teensy socket GND pin must beep.",
        "Plug A pin 1 to Teensy pin 27 must beep; B pin 1 to 28, C to 29, D to 30 (enable).",
        "Plug A pin 2 to the DAC's VA pin must beep; B to VB, C to VC, D to VD (setpoint).",
        "Plug A pin 5 to Teensy pin 14 reads 1 kOhm (resistance mode); B to 15, C to 16, D to 17 (force).",
        "Plug A pin 5 to plug A pin 1 reads about 1 MOhm (the pull-up); same for B, C, D.",
        "DAC SCL to Teensy pin 19 and DAC SDA to Teensy pin 18 must beep (through W2 and W1).",
        "Then Teensy + DAC in, USB only: bumpem monitor --port <PORT> shows telemetry and no 'DAC init failed'.",
    ])
    pdf.savefig(fig); plt.close(fig)


if __name__ == "__main__":
    out = HERE / "fab/bumpem-carrier-milled-soldering.pdf"
    link_txt = {"W1": "SDA", "W2": "SCL", "W3": "3.3 V", "W4": "enable B", "W5": "setpoint A", "W6": "setpoint B", "W7": "setpoint C"}
    with PdfPages(out) as pdf:
        page_intro(pdf)
        page_step(pdf, 1, "wire links W1-W7 (7 wires, 14 joints)",
                  "Insulated wire on the TOP side, ends through the two holes, soldered underneath. " +
                  ", ".join(f"{r} = {link_txt.get(r, '')}" for r in LINKS) + ". W1-W3 sit under the Teensy: fit them first, flat.",
                  LINKS, [
                  "Cut a piece of insulated wire 1 cm longer than the distance between the two holes; strip 4 mm at each end.",
                  "Push the ends through from the top, wire lying flat on the board. W1 and W2 cross each other: that is "
                  "intended (insulated wires, different signals).",
                  "Turn over, bend the ends slightly so they stay, solder the 14 green-ringed pads, cut the ends ~1 mm above the joint.",
                  "Check each with the multimeter (beep from one end's pad to the other)."], all_links=True)
        page_step(pdf, 2, "R1-R4, 1 kOhm (8 joints)", "Drawer \"1 K\": brown-black-black-BROWN-brown. Either way round. "
                  "R1, R2, R3 stand vertically, R4 lies horizontally; R2's holes are 15 mm apart (bend the legs further out).",
                  ["R1", "R2", "R3", "R4"], [
                  "Bend the legs to the hole spacing, push in until the body lies on the board (over the tracks between its holes).",
                  "Turn over, solder the 8 green-ringed pads, cut the legs."])
        page_step(pdf, 3, "R5-R8, 1 MOhm (8 joints)", "Drawer \"1 M\": brown-black-black-YELLOW-brown. Either way round. "
                  "One just above each plug, horizontal.", ["R5", "R6", "R7", "R8"], [
                  "Same as step 2: bend, push in flat, turn over, solder, cut."])
        page_step(pdf, 4, "Teensy socket U1 (12 joints)", "Two whole 1 x 24 female headers. Only 12 holes have a copper ring "
                  "(6 per row): solder those, leave the other pins dry.", ["U1"], [
                  "Plug both headers onto the Teensy, set Teensy + headers in from the top (USB at the left edge).",
                  "Turn over, solder one green pad at each end of each row, check the headers sit flat, pull the Teensy out.",
                  "Solder the remaining green pads. The bare holes get no solder."])
        page_step(pdf, 5, "DAC socket U2 (8 joints)", "Two 1 x 6 female headers. Chip side of the DAC up, I2C row (SCL/SDA) "
                  "away from the plugs, VA-VD row towards them.", ["U2"], [
                  "Same as step 4 with the DAC board: set in, tack one pad per row, check flat, pull the DAC out, solder the rest."])
        page_step(pdf, 6, "module plugs J1-J4 (20 joints)", "Green Phoenix headers along the near edge, A-D from the left seen "
                  "from the top; the opening for the cable plug faces OUT over the edge.", ["J1", "J2", "J3", "J4"], [
                  "Push each header in, flat and square to the edge; solder one end pin, check, then the other 4.",
                  "Big pins: hold the iron 3-4 s, enough solder for a full cone. Short heat on unplated pads (they can lift)."])
        page_check(pdf)
    print("written", out)

"""Assembly guide for the printed tower holders: what goes on each tower, where, in which order.
Run after overview.py (it reuses out/renders/):  python assembly_guide.py  ->  out/assembly-guide.pdf"""
import textwrap
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import FancyArrowPatch, Rectangle

import parts

OUT = Path(__file__).parent / "out"
R = OUT / "renders"
A4 = (8.27, 11.69)
BLUE, AMBER, GREY, RED = "#8ca8cc", "#eb735a", "#c7c9cc", "#b3261e"


def text(fig, x, y, s, width=95, size=9.5, gap=0.016, **kw):
    """Wrapped text from the top; returns the y below it."""
    for line in textwrap.wrap(s, width):
        fig.text(x, y, line, fontsize=size, **kw)
        y -= gap
    return y


def steps(fig, x, y, items, width=88, size=9.5):
    for n, s in enumerate(items, 1):
        fig.text(x, y, f"{n}.", fontsize=size, weight="bold")
        y = text(fig, x + 0.03, y, s, width, size) - 0.006
    return y


def table(fig, y, head, rows, xs, size=9):
    for x, h in zip(xs, head):
        fig.text(x, y, h, fontsize=size, weight="bold")
    y -= 0.006
    fig.add_artist(plt.Line2D([xs[0], 0.93], [y, y], color="#999", lw=0.6, transform=fig.transFigure))
    y -= 0.018
    for row in rows:
        lines = [textwrap.wrap(c, w) for c, w in zip(row, (25, 24, 24, 24))]
        for x, ls in zip(xs, lines):
            for k, l in enumerate(ls):
                fig.text(x, y - k * 0.014, l, fontsize=size)
        y -= 0.014 * max(len(l) for l in lines) + 0.008
    return y


def page_overview(pdf):
    fig = plt.figure(figsize=A4)
    fig.text(0.07, 0.95, "Printed holders: what goes where", fontsize=18, weight="bold")
    y = text(fig, 0.07, 0.925, "Every tower gets the same three holders. Each holder carries one device that is taped to the tower now; "
             "the chopper, ESCON and motor unit stay where they are.", 100)
    y -= 0.01
    y = table(fig, y, ["Printed part (file)", "Device it carries", "Device held by", "Holder fixed to tower by"], [
        ["DIN-rail mount (iaa100_din_mount.stl)", "Futek IAA100 force amplifier (small black box, load-cell cable)", "nothing: the IAA100 clicks onto the rail", "2 x M6x16 + 2 T-nuts, one slot"],
        ["24 V plate (rs15_plate.stl)", "Mean Well RS-15-24 (small 24 V supply)", "2 x M3x6 from the back", "2 x M6x16 + 2 T-nuts, one slot"],
        ["48 V brackets A + B (rsp2000_brackets.stl)", "Mean Well RSP-2000-48 (large 48 V supply, 1.95 kg)", "A: 2 x M4x12, B: 1 x M4x12, from the back", "2 x M6x16 + 2 T-nuts each, both slots of one face"],
    ], [0.07, 0.30, 0.51, 0.72])
    y -= 0.01
    fig.text(0.07, y, "Per tower / for all 4 towers", fontsize=11, weight="bold"); y -= 0.022
    y = text(fig, 0.07, y, "Printed: 1 DIN-rail mount, 1 24 V plate, 1 pair of 48 V brackets  /  4, 4, 4 pairs.", 100)
    y = text(fig, 0.07, y, "Screws: 8 x M6x16 button head, 8 slot-10 T-nuts, 2 x M3x6, 3 x M4x12  /  32, 32, 8, 12.", 100)
    y -= 0.012
    fig.text(0.07, y, "Before you start", fontsize=11, weight="bold"); y -= 0.022
    y = steps(fig, 0.07, y, [
        "Power: the tower's power strip unplugged from the wall. Mains wiring (230 V side of both supplies) stays with the electrician.",
        "T-nuts: slide-in T-nuts only go in from the end of the profile. If the profile ends are blocked (motor unit on top, floor "
        "mount at the bottom), use drop-in (swivel / hammer-head) slot-10 T-nuts: they go in from the front and turn 90 degrees when tightened.",
        "Fit test first: push the test plate's key (the ridge on its back) into a slot. It must slide without play. Too tight or loose: tell Claude before printing the rest.",
        "Always fit the device to its holder first, then the holder to the tower.",
    ])
    y -= 0.01
    fig.text(0.07, y, "Words used", fontsize=11, weight="bold"); y -= 0.022
    steps(fig, 0.07, y, [
        "Key: the 9.6 mm ridge on the back of each holder. It sits in the profile slot and stops the holder from turning.",
        "Slot: the groove along each face of the aluminium profile. Each 90 mm face has two slots, 45 mm apart.",
        "Face: one of the four flat sides of the tower profile.",
    ])
    pdf.savefig(fig); plt.close(fig)


def page_layout(pdf):
    fig = plt.figure(figsize=A4)
    fig.text(0.07, 0.95, "Where on the tower (recommended)", fontsize=18, weight="bold")
    text(fig, 0.07, 0.925, "Heights are not fixed: put each holder where its cables reach without strain. If a device is already taped "
         "at a spot that works, put its holder right there. The layout below is the recommended starting point.", 105)

    # top view: which face
    ax = fig.add_axes([0.06, 0.58, 0.40, 0.27]); ax.set_aspect("equal"); ax.set_axis_off()
    ax.add_patch(Rectangle((-45, -45), 90, 90, color=GREY))
    for s in (-22.5, 22.5):
        for (x, y_, w, h) in ((s - 5, 37, 10, 8), (s - 5, -45, 10, 8), (37, s - 5, 8, 10), (-45, s - 5, 8, 10)):
            ax.add_patch(Rectangle((x, y_), w, h, color="white"))
    ax.add_patch(Rectangle((-45, 46), 90, 10, color="#555")); ax.text(0, 51, "motor unit, rope", ha="center", va="center", color="white", fontsize=8)
    ax.add_artist(FancyArrowPatch((0, 58), (0, 95), arrowstyle="-|>", mutation_scale=12, color=RED))
    ax.text(0, 98, "treadmill / subject", ha="center", fontsize=9, color=RED)
    ax.add_patch(Rectangle((-45, -56), 90, 10, color=BLUE)); ax.text(0, -51, "holders", ha="center", va="center", fontsize=8)
    ax.text(0, -66, "back face: electronics", ha="center", fontsize=9, weight="bold")
    ax.set_xlim(-80, 80); ax.set_ylim(-75, 108)
    ax.set_title("Seen from above", fontsize=10)
    text(fig, 0.06, 0.565, "Put the holders on the face pointing away from the treadmill: the rope side stays clear and nobody on the "
         "treadmill can touch the 48 V parts. A side face is fine if the back is blocked.", 52, 8.5, 0.014)

    # front view of the back face
    ax = fig.add_axes([0.52, 0.04, 0.42, 0.80]); ax.set_aspect("equal"); ax.set_axis_off()
    H = 1500
    ax.add_patch(Rectangle((-45, 0), 90, H, color=GREY))
    for s in (-22.5, 22.5):
        ax.add_patch(Rectangle((s - 5, 0), 10, H, color="#e6e7e9"))
    ax.add_patch(Rectangle((-60, H - 160), 120, 160, color="#555")); ax.text(0, H - 80, "motor unit\n(other face)", ha="center", va="center", color="white", fontsize=8)

    def holder(y0, h, x0, w, label, dev, side):
        ax.add_patch(Rectangle((x0, y0), w, h, color=AMBER, alpha=0.5))
        ax.add_patch(Rectangle((x0 + w / 2 - 12, y0 + 4), 24, h - 8, color=BLUE))
        xt = 80 if side > 0 else -80
        ax.annotate(f"{label}\n{dev}", (x0 + w / 2 + side * w / 2, y0 + h / 2), (xt, y0 + h / 2), fontsize=8,
                    ha="left" if side > 0 else "right", va="center", arrowprops=dict(arrowstyle="-", color="#333", lw=0.6))

    holder(1050, 100, -42.5, 40, "DIN-rail mount", "IAA100 (amplifier)\nnear the load-cell cable", 1)
    holder(880, 120, -48, 51, "24 V plate", "RS-15-24\nright under the IAA100:\nshort 24 V wires", -1)
    ax.add_patch(Rectangle((-63.5, 180), 127, 295, color=AMBER, alpha=0.5))           # RSP-2000 outline
    for yb in (180 - 24, 475 - 38):                                                    # brackets: 62 mm, 24 beyond each end
        ax.add_patch(Rectangle((-43, yb), 86, 62, color=BLUE))
    ax.annotate("48 V brackets A + B (blue)\nRSP-2000-48 (red), lowest:\nheaviest part; fans free;\nnear chopper + power strip",
                (63.5, 330), (80, 330), fontsize=8, ha="left", va="center", arrowprops=dict(arrowstyle="-", color="#333", lw=0.6))
    ax.text(0, 60, "floor mount", ha="center", fontsize=8)
    ax.set_xlim(-200, 200); ax.set_ylim(0, H + 30)
    ax.set_title("Back face from behind\n(heights not to scale)", fontsize=10)

    y = 0.50
    fig.text(0.06, y, "Rules behind the layout", fontsize=11, weight="bold"); y -= 0.022
    steps(fig, 0.06, y, [
        "IAA100: within reach of the load-cell cable (the load cell hangs in the rope near the eyebolt), and of the 5-wire signal cable.",
        "RS-15-24 next to the IAA100: its +V / -V go to IAA100 pins 1 / 2. Its 230 V terminals face away from hands; the electrician covers them.",
        "IAA100 and RS-15 use the same slot, one above the other (side by side they would overlap by 0.5 mm).",
        "RSP-2000 low on the tower: 1.95 kg, close to the power strip and to the chopper (its +V / -V go to chopper pins 4 / 5). "
        "Hang it along the profile, both brackets in both slots, fans at the ends not blocked, 10 mm air gap behind.",
        "Leave a hand's width free around the chopper and ESCON: they get warm.",
    ], 50, 8.5)
    pdf.savefig(fig); plt.close(fig)


def page_part(pdf, title, render_name, guide_key, extra):
    fig = plt.figure(figsize=A4)
    fig.text(0.07, 0.95, title, fontsize=18, weight="bold")
    for rect, img, cap in (([0.03, 0.62, 0.46, 0.30], R / f"{render_name}.png", "The printed part"),
                           ([0.51, 0.62, 0.46, 0.30], R / f"{render_name} mounted.png", "On the profile (grey), device (red)")):
        ax = fig.add_axes(rect); ax.imshow(plt.imread(img)); ax.set_axis_off(); ax.set_title(cap, fontsize=9, color="#555")
    role, todo = parts.GUIDE[guide_key]
    y = text(fig, 0.07, 0.60, role, 100)
    y -= 0.012
    fig.text(0.07, y, "Steps", fontsize=11, weight="bold"); y -= 0.022
    y = steps(fig, 0.07, y, todo)
    y -= 0.01
    fig.text(0.07, y, "Check", fontsize=11, weight="bold"); y -= 0.022
    text(fig, 0.07, y, extra, 100)
    pdf.savefig(fig); plt.close(fig)


if __name__ == "__main__":
    out = OUT / "assembly-guide.pdf"
    with PdfPages(out) as pdf:
        page_overview(pdf)
        page_layout(pdf)
        page_part(pdf, "1. IAA100 on the DIN-rail mount", "IAA100 DIN-rail mount", "IAA100 DIN-rail mount",
                  "Push the amplifier: it does not move. Load-cell cable and signal cable reach without pulling.")
        page_part(pdf, "2. RS-15-24 on the 24 V plate", "24 V supply plate (RS-15-24)", "24 V supply plate (RS-15-24)",
                  "Supply sits flat against the end stop; screws not longer than M3x6 (max 3 mm into the case). 230 V terminals covered before the strip is plugged in.")
        page_part(pdf, "3. RSP-2000-48 on the two brackets", "48 V supply brackets (RSP-2000-48)", "48 V supply brackets (RSP-2000-48)",
                  "Two people. Push the supply: nothing moves, keys sit in both slots. Fans and vents free, 10 mm gap behind. Output cables reach chopper pins 4 / 5 without strain.")
    print("written", out)

"""Picture guide: which part of the motor unit slips (Stanford motor unit, docs/reference/stanford-cad/1) Motor Unit).
Run: python slip_check_guide.py  ->  slip-check-guide.pdf (needs numpy + matplotlib)."""
import os
import struct
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Circle, FancyBboxPatch, Polygon, Rectangle
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

HERE = Path(__file__).parent
CAD = HERE.parent.parent / "docs/reference/stanford-cad/1) Motor Unit"
A4 = (8.27, 11.69)
STEEL, DARK, PRINT, RUBBER, ROPE, MARK, WARN = "#b8bec6", "#3a3f45", "#f0c419", "#e2553c", "#2f7fc1", "#111111", "#c0392b"


def stl(path):
    """Triangles of a binary STL (Stanford files have a 'solid' header but are binary)."""
    b = path.read_bytes()
    n = struct.unpack("<I", b[80:84])[0]
    a = np.frombuffer(b, dtype=np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("x", "<u2")]), count=n, offset=84)
    return a["v"] * 25.4                                          # inch -> mm


def text_page(pdf, title, lines, size=11):
    fig = plt.figure(figsize=A4); fig.text(0.07, 0.95, title, fontsize=17, weight="bold", va="top")
    y = 0.90
    for ln in lines:
        bold = ln.startswith("**")
        ln = ln.strip("*")
        fig.text(0.07, y, ln, fontsize=size, va="top", weight="bold" if bold else "normal", wrap=True)
        y -= 0.028 if ln else 0.014
    pdf.savefig(fig); plt.close(fig)


# ---------------------------------------------------------------- drawings (side view, shaft horizontal)
def motor(ax, x, y, h=2.6):
    ax.add_patch(FancyBboxPatch((x, y - h / 2), 1.0, h, boxstyle="round,pad=0,rounding_size=0.15", fc=DARK, ec="k"))
    ax.add_patch(Rectangle((x + 0.1, y + h / 2 - 0.05), 0.25, 0.5, fc="#777", ec="k"))   # cable gland
    ax.plot([x + 0.22, x + 0.22, x - 0.4], [y + h / 2 + 0.45, y + h / 2 + 0.9, y + h / 2 + 0.9], color="#555", lw=3)


def shaft(ax, x0, x1, y, d=0.22, c=STEEL):
    ax.add_patch(Rectangle((x0, y - d / 2), x1 - x0, d, fc=c, ec="#666"))


def coupler(ax, x, y):
    """Spider (jaw) coupling: two metal hubs with interlocking jaws and a rubber spider."""
    for hx in (x, x + 0.95):
        ax.add_patch(Rectangle((hx, y - 0.5), 0.55, 1.0, fc=STEEL, ec="#555"))
        ax.add_patch(Circle((hx + 0.28, y + 0.5), 0.07, fc=DARK))                 # set screw on top
    for k in range(3):                                                              # jaws
        yy = y - 0.45 + k * 0.32
        ax.add_patch(Rectangle((x + 0.55, yy), 0.22, 0.2, fc=STEEL, ec="#555"))
        ax.add_patch(Rectangle((x + 0.73, yy + 0.16), 0.22, 0.2, fc=STEEL, ec="#555"))
    ax.add_patch(Rectangle((x + 0.6, y - 0.42), 0.3, 0.84, fc=RUBBER, ec="#7a2a1c", alpha=0.85))


def bearing_mount(ax, x, y):
    ax.add_patch(Rectangle((x, y - 1.8), 0.35, 3.6, fc=PRINT, ec="#9a7d0a"))
    ax.add_patch(Rectangle((x - 0.08, y - 0.35), 0.5, 0.7, fc="#d0d4da", ec="#555"))   # flanged bearing


def collar(ax, x, y):
    ax.add_patch(Rectangle((x, y - 0.45), 0.35, 0.9, fc=STEEL, ec="#555"))           # clamp ring
    ax.add_patch(Rectangle((x + 0.35, y - 0.8), 0.12, 1.6, fc=STEEL, ec="#555"))     # flange
    ax.plot([x + 0.17, x + 0.17], [y + 0.45, y + 0.6], color=DARK, lw=4)             # clamp screw head
    for yy in (y - 0.6, y + 0.6):
        ax.add_patch(Rectangle((x + 0.47, yy - 0.05), 0.35, 0.1, fc=DARK))         # screws into the drum


def drum(ax, x, y, wraps=True):
    ax.add_patch(Rectangle((x, y - 1.6), 0.18, 3.2, fc=PRINT, ec="#9a7d0a"))         # flange
    ax.add_patch(Rectangle((x + 0.18, y - 0.95), 1.0, 1.9, fc=PRINT, ec="#9a7d0a"))  # core (rope surface)
    ax.add_patch(Rectangle((x + 1.18, y - 1.6), 0.18, 3.2, fc=PRINT, ec="#9a7d0a"))
    if wraps:
        for k in range(6):
            ax.plot([x + 0.24 + k * 0.16] * 2, [y - 0.95, y + 0.95], color=ROPE, lw=2.2)
    ax.add_patch(Circle((x + 0.68, y), 0.1, fc="white", ec="#9a7d0a"))               # tie hole


def number(ax, x, y, n, c=WARN):
    ax.add_patch(Circle((x, y), 0.22, fc=c, ec="white", lw=1.5, zorder=10))
    ax.text(x, y, str(n), color="white", ha="center", va="center", fontsize=11, weight="bold", zorder=11)


def drivetrain(ax, y=0, marks=False, broken_at=None):
    """Whole motor unit, side view. Returns x positions of the joints."""
    motor(ax, 0, y); shaft(ax, 1.0, 1.9, y, 0.26)
    coupler(ax, 1.6, y); shaft(ax, 3.1, 8.0, y)
    bearing_mount(ax, 4.0, y); bearing_mount(ax, 7.5, y)
    collar(ax, 5.0, y); drum(ax, 5.85, y)
    ax.plot([6.85, 6.85, 9.0], [y - 0.95, y - 2.3, y - 2.3], color=ROPE, lw=2.5)   # rope leaving the drum
    joints = {1: 1.75, 2: 2.75, 3: 5.15, 4: 5.65}
    if marks:                                                                       # the marker line
        segs = [(0.6, 1.75), (1.75, 2.75), (2.75, 5.15), (5.15, 5.65), (5.65, 7.0)]
        for i, (a, b) in enumerate(segs):
            off = 0.0 if broken_at is None or i < broken_at else 0.45
            ax.plot([a, b], [y + 0.15 + off, y + 0.15 + off], color=MARK, lw=3, solid_capstyle="butt", zorder=8)
    return joints


def overview(pdf):
    fig = plt.figure(figsize=A4)
    fig.text(0.07, 0.95, "Motor unit: what turns the rope", fontsize=17, weight="bold", va="top")
    fig.text(0.07, 0.915, "Side view of one tower's motor unit (Stanford design; IBMS drums are printed from the same file).\n"
             "The motor turns the parts from left to right. Red numbers = the 4 places where it can slip.",
             fontsize=10.5, va="top")
    ax = fig.add_axes([0.04, 0.48, 0.92, 0.40]); ax.set_xlim(-0.6, 9.3); ax.set_ylim(-3.2, 3.0); ax.set_aspect("equal"); ax.axis("off")
    j = drivetrain(ax)
    for n, x in j.items():
        number(ax, x, 1.45 if n != 3 else 1.25, n)
    lab = [(0.5, -1.9, "Motor\n(round, black,\nwith a cable)"), (2.2, -1.1, "Spider coupler\n(2 metal cups +\nred rubber star)"),
           (4.2, -2.2, "Bearing in the\nprinted mount"), (5.25, 1.75, "Shaft collar"), (6.5, 2.0, "Reel drum\n(printed spool)"),
           (8.2, -2.0, "Rope"), (3.6, 0.45, "Drive shaft")]
    for x, yy, t in lab:
        ax.text(x, yy, t, ha="center", va="center", fontsize=9)
    rows = [("1", "Motor shaft → coupler", "the coupler's left cup turns on the motor shaft"),
            ("2", "Coupler → drive shaft", "the coupler's right cup turns on the drive shaft"),
            ("3", "Drive shaft → shaft collar", "the collar turns on the drive shaft\n(clamp screw loose)"),
            ("4", "Shaft collar → reel drum", "the drum turns on the collar\n(screws loose or plastic torn)"),
            ("–", "Rope → drum", "the rope slides on the drum\n(knot not held, too few turns)")]
    y = 0.43
    fig.text(0.07, y, "Where it can slip", fontsize=13, weight="bold", va="top"); y -= 0.035
    for n, a, b in rows:
        fig.text(0.08, y, n, fontsize=11, weight="bold", color=WARN, va="top")
        fig.text(0.12, y, a, fontsize=10.5, weight="bold", va="top")
        fig.text(0.45, y, b, fontsize=9.5, va="top"); y -= 0.04
    y -= 0.01
    fig.text(0.07, y, "Your description (the drum stops when the rope gets tight, the motor\nspeeds up) fits 3 or 4 best.",
             fontsize=10.5, va="top", weight="bold")
    fig.text(0.07, y - 0.05, "Bearings never hold the drum: they only let the shaft spin. Not a slip point.", fontsize=10, va="top")
    fig.text(0.07, 0.07, "SAFETY: disarm in the UI, then switch the tower's 48 V OFF\nbefore touching the motor unit.",
             fontsize=11, weight="bold", color=WARN)
    pdf.savefig(fig); plt.close(fig)


# ---------------------------------------------------------------- one card per part
def card(fig, rect, title, draw, look, check):
    x, y, w, h = rect
    fig.patches.append(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.004", transform=fig.transFigure,
                                      fc="#f7f7f7", ec="#bbb", zorder=-10))
    fig.text(x + 0.012, y + h - 0.012, title, fontsize=12, weight="bold", va="top")
    ax = fig.add_axes([x + 0.01, y + 0.30 * h, 0.42 * w, 0.58 * h]); ax.axis("off"); ax.set_aspect("equal")
    draw(ax)
    fig.text(x + 0.47 * w, y + h - 0.045, "Looks like", fontsize=9.5, weight="bold", va="top")
    fig.text(x + 0.47 * w, y + h - 0.065, look, fontsize=8.5, va="top")
    fig.text(x + 0.012, y + 0.27 * h, "Check", fontsize=9.5, weight="bold", va="top", color=WARN)
    fig.text(x + 0.012, y + 0.27 * h - 0.02, check, fontsize=8.5, va="top")


def d_motor(ax):
    motor(ax, 0, 0); shaft(ax, 1.0, 2.0, 0, 0.3); ax.set_xlim(-0.6, 2.4); ax.set_ylim(-1.8, 2.0)
    ax.annotate("motor shaft\n(10 mm steel)", (1.7, -0.15), (1.1, -1.6), fontsize=8, arrowprops=dict(arrowstyle="->"))


def d_coupler(ax):
    shaft(ax, -0.3, 0.2, 0, 0.3); coupler(ax, 0, 0); shaft(ax, 1.5, 2.0, 0)
    ax.set_xlim(-0.4, 2.1); ax.set_ylim(-1.0, 1.3)
    ax.annotate("set screw", (0.28, 0.55), (-0.3, 1.1), fontsize=8, arrowprops=dict(arrowstyle="->"))
    ax.annotate("rubber star", (0.75, -0.3), (1.0, -0.9), fontsize=8, arrowprops=dict(arrowstyle="->"))


def d_shaft(ax):
    shaft(ax, 0, 3.0, 0, 0.3); ax.add_patch(Rectangle((2.2, 0.09), 0.6, 0.06, fc="#888"))
    ax.set_xlim(-0.2, 3.2); ax.set_ylim(-1.2, 0.9)
    ax.annotate("flat (if any): screws\nshould press on it", (2.5, 0.09), (0.0, -1.0), fontsize=8, arrowprops=dict(arrowstyle="->"))


def d_collar(ax):
    shaft(ax, -0.4, 1.0, 0); collar(ax, 0, 0); ax.set_xlim(-0.5, 1.1); ax.set_ylim(-1.0, 1.2)
    ax.annotate("clamp screw", (0.17, 0.6), (-0.45, 1.05), fontsize=8, arrowprops=dict(arrowstyle="->"))
    ax.annotate("screws into\nthe drum", (0.7, -0.6), (0.55, -1.0), fontsize=8, arrowprops=dict(arrowstyle="->"))


def d_rope(ax):
    drum(ax, 0, 0, wraps=True)
    ax.plot([0.68, 0.68], [0, 0.95], color=ROPE, lw=2); ax.add_patch(Circle((0.68, -0.15), 0.13, fc=ROPE))
    ax.set_xlim(-0.3, 1.7); ax.set_ylim(-1.8, 1.8)
    ax.annotate("knot (figure 8)\ninside the core", (0.68, -0.15), (1.2, -1.5), fontsize=8, arrowprops=dict(arrowstyle="->"))


def d_drum3d(fig, rect):
    tri = stl(CAD / "Reel Drum.STL")
    ax = fig.add_axes(rect, projection="3d"); ax.axis("off")
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]); n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-9
    shade = 0.45 + 0.55 * np.clip(np.nan_to_num(n @ np.array([0.4, -0.5, 0.75])), 0, 1)
    cols = np.c_[np.outer(shade, matplotlib.colors.to_rgb(PRINT)), np.ones(len(shade))]
    ax.add_collection3d(Poly3DCollection(tri, facecolors=cols, edgecolor="none"))
    lo, hi = tri.reshape(-1, 3).min(0), tri.reshape(-1, 3).max(0); c = (lo + hi) / 2; r = (hi - lo).max() / 2
    ax.set_xlim(c[0] - r, c[0] + r); ax.set_ylim(c[1] - r, c[1] + r); ax.set_zlim(c[2] - r, c[2] + r)
    ax.view_init(elev=25, azim=35)


def cards(pdf):
    fig = plt.figure(figsize=A4)
    fig.text(0.07, 0.965, "The parts, one by one", fontsize=17, weight="bold", va="top")
    W, H, X1, X2 = 0.42, 0.29, 0.06, 0.52
    card(fig, (X1, 0.64, W, H), "Motor + motor shaft", d_motor,
         "Flat round motor\n(maxon EC 90 flat, 9 cm),\nthick cable on it.\nThe short steel pin in\nthe middle is the\nmotor shaft.",
         "Nothing to tighten on the motor itself.\nIt is where the marker line starts.")
    card(fig, (X2, 0.64, W, H), "1–2  Spider coupler", d_coupler,
         "Two metal cups facing\neach other, claws\ninterlocking, a coloured\nrubber star between.\nEach cup has a small\nscrew on its side (or a\nslot with a clamp screw).",
         "Joint 1 = left cup on the motor shaft.\nJoint 2 = right cup on the drive shaft.\nTighten both screws (hex key).")
    card(fig, (X1, 0.33, W, H), "Drive shaft", d_shaft,
         "Plain steel rod\n(about 9.5 mm thick)\nfrom the coupler,\nthrough the bearings in\nthe printed mount,\nto the drum.",
         "If it has a flat side, the coupler and\ncollar screws must press on the flat.")
    card(fig, (X2, 0.33, W, H), "3–4  Flanged shaft collar", d_collar,
         "Metal ring with a slit\nand one screw across it\n(the clamp), plus a flat\ndisc with small holes.\nThe disc is screwed\nonto the drum.",
         "Joint 3 = ring on the shaft:\ntighten the clamp screw firmly.\nJoint 4 = disc on the drum:\ntighten the small screws\n(torn plastic: see page 4).")
    card(fig, (X1, 0.02, W, H), "Rope on the drum", d_rope,
         "The rope goes through\nthe small hole in the\ndrum core; a knot\ninside stops it.\nSeveral turns stay on\nthe drum when tight.",
         "Knot holds? At least 3 turns left on the\ndrum at full tension?")
    x, y = X2, 0.02
    fig.patches.append(FancyBboxPatch((x, y), W, H, boxstyle="round,pad=0.004", transform=fig.transFigure, fc="#f7f7f7", ec="#bbb", zorder=-10))
    fig.text(x + 0.012, y + H - 0.012, "Reel drum (3D, from the print file)", fontsize=12, weight="bold", va="top")
    d_drum3d(fig, [x + 0.01, y + 0.06, W - 0.02, H - 0.08])
    fig.text(x + 0.012, y + 0.02, "Printed spool: rope surface 38 mm,\nflanges 64 mm, tie hole 5.6 mm.", fontsize=9)
    pdf.savefig(fig); plt.close(fig)


def marker_test(pdf):
    fig = plt.figure(figsize=A4)
    fig.text(0.07, 0.95, "Find the slip: the marker-line test", fontsize=17, weight="bold", va="top")
    steps = ["1. 48 V OFF for this tower (disarm first).",
             "2. Draw ONE straight line with a permanent marker along the motor shaft, both coupler cups,",
             "    the drive shaft, the shaft collar and the drum (top picture).",
             "3. Hold the drum firmly and turn the motor by hand, hard (or: hold the motor, turn the drum).",
             "4. Look where the line no longer lines up: that joint slips (bottom picture: joint 3)."]
    for i, s in enumerate(steps):
        fig.text(0.07, 0.905 - i * 0.025, s, fontsize=10.5, va="top")
    for k, (yy, br, t) in enumerate([(0.53, None, "Before: one straight line"), (0.27, 3, "After: line broken at joint 3 (collar turned on the shaft)")]):
        ax = fig.add_axes([0.04, yy, 0.92, 0.23]); ax.set_xlim(-0.6, 9.3); ax.set_ylim(-2.6, 2.4); ax.set_aspect("equal"); ax.axis("off")
        j = drivetrain(ax, marks=True, broken_at=br)
        for n, x in j.items():
            number(ax, x, -1.3, n, c="#888" if br is None or n != br else WARN)
        ax.set_title(t, fontsize=11, weight="bold", loc="left")
    rows = [("1", "coupler cup on the motor shaft", "tighten the left cup's screw (on the flat if there is one)"),
            ("2", "coupler cup on the drive shaft", "tighten the right cup's screw"),
            ("3", "collar on the drive shaft", "tighten the collar's clamp screw firmly"),
            ("4", "drum on the collar", "tighten the small screws; if they spin\nfreely, the plastic is torn (page 4)")]
    y = 0.255
    fig.text(0.07, y, "Line breaks at …", fontsize=12, weight="bold", va="top"); y -= 0.03
    for n, a, b in rows:
        fig.text(0.08, y, n, fontsize=11, weight="bold", color=WARN, va="top")
        fig.text(0.12, y, a, fontsize=10, weight="bold", va="top")
        fig.text(0.45, y, b, fontsize=9.5, va="top"); y -= 0.031
    fig.text(0.07, 0.035, "Line intact everywhere but the rope still slips?\nThen the rope slides on the drum: check the knot and the turns.",
             fontsize=10, weight="bold")
    pdf.savefig(fig); plt.close(fig)


class Pages(PdfPages):
    """PdfPages that also writes page PNGs when PREVIEW=<dir> is set (for checking the layout)."""
    n = 0
    def savefig(self, fig, **kw):
        super().savefig(fig, **kw)
        if os.environ.get("PREVIEW"):
            Pages.n += 1; fig.savefig(Path(os.environ["PREVIEW"]) / f"page{Pages.n}.png", dpi=70)


if __name__ == "__main__":
    out = HERE / "slip-check-guide.pdf"
    with Pages(out) as pdf:
        overview(pdf)
        cards(pdf)
        marker_test(pdf)
        text_page(pdf, "If the drum's screws spin in the plastic", [
            "**The print is torn where the collar screws go in. Options, easiest first:",
            "",
            "• Longer screws all the way through the drum, with a nut and washer on the other side.",
            "• Heat-set threaded inserts in the drum (soldering iron, a few minutes per insert).",
            "• Reprint the drum: 100 % infill (or 6+ walls) around the centre, PETG or ABS, not PLA.",
            "",
            "**After any fix",
            "",
            "• Redraw the marker line, power the tower, do one test pull (testing page, 30 N, 1 s).",
            "• The line must still be straight afterwards. Then 50 N, then 100 N.",
            "",
            "**Record what you found",
            "",
            "• Which tower, which joint, what you changed: tell Claude, it goes into docs/STATUS.md.",
            "• A phone photo of the joint helps (docs/hardware-photos/).",
            "",
            "Drawings follow Stanford's motor unit (docs/reference/stanford-cad/1) Motor Unit):",
            "spider coupler 10 mm / 3/8 in, drive shaft in flanged bearings, flanged shaft collar on the drum.",
            "If your tower looks different, send a photo and the guide gets updated.",
        ])
    print("written", out)

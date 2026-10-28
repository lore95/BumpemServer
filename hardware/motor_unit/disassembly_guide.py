"""Take the reel drum off a motor unit (and put it back), on the user's photo of tower B (2026-10-28).
Run: python disassembly_guide.py  ->  disassembly-guide.pdf (needs numpy, matplotlib, Pillow; PREVIEW=<dir> also writes PNGs)."""
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, FancyBboxPatch, Rectangle
from PIL import Image, ImageOps

from slip_check_guide import A4, HERE, PRINT, ROPE, STEEL, WARN, Pages

PHOTO = HERE / "photos/motor_unit_B_2026-10-28.jpg"
OK, NO = "#1f8a4c", WARN

# label: (text, point on the photo (x, y) in pixels of the upright 1200 x 1600 image, label position, colour)
LABELS = {
    "A": ("Reel drum (rope spool)", (290, 900), (60, 1350), OK),
    "B": ("Drum hub: 3 bolts #6-32 to the collar\n(one missing), 7/64\" hex key", (440, 745), (60, 600), WARN),
    "C": ("Silver ring = flanged bearing\n(lets the shaft spin, nothing to undo)", (565, 870), (520, 1250), OK),
    "D": ("Printed motor mount (wall)", (655, 960), (660, 1450), OK),
    "E": ("Coupler, drum-side half\n(clamp screw on top)", (745, 802), (560, 610), WARN),
    "F": ("Red rubber star (spider)", (850, 880), (860, 1060), OK),
    "G": ("Coupler, motor-side half\n(clamp screw, leave it)", (990, 782), (880, 610), OK),
    "H": ("Motor shaft → motor", (1060, 885), (980, 1180), OK),
    "I": ("Mount screws (leave them)", (750, 425), (800, 330), OK),
}


def photo_page(pdf):
    fig = plt.figure(figsize=A4)
    fig.text(0.07, 0.965, "Your motor unit (tower B), part by part", fontsize=16, weight="bold", va="top")
    fig.text(0.07, 0.94, "Red = you work on it.  Green = leave it alone.", fontsize=10.5, va="top")
    img = np.asarray(ImageOps.exif_transpose(Image.open(PHOTO)))
    ax = fig.add_axes([0.03, 0.03, 0.94, 0.89]); ax.imshow(img); ax.axis("off")
    for k, (txt, (px, py), (lx, ly), col) in LABELS.items():
        ax.add_patch(Circle((px, py), 18, fc="none", ec=col, lw=2.5))
        ax.annotate(f"{k}  {txt}", (px, py), (lx, ly), fontsize=8.5, color="white", weight="bold",
                    bbox=dict(boxstyle="round,pad=0.3", fc=col, ec="none", alpha=0.9),
                    arrowprops=dict(arrowstyle="-", color=col, lw=2))
    pdf.savefig(fig); plt.close(fig)


def steps_page(pdf, title, lines, note=None):
    fig = plt.figure(figsize=A4)
    fig.text(0.07, 0.95, title, fontsize=16, weight="bold", va="top")
    y = 0.90
    for s in lines:
        head, stop = s.startswith("#"), s.startswith("!")
        s = s.lstrip("#!")
        fig.text(0.07, y, s, fontsize=11.5 if head else 10.5, va="top",
                 weight="bold" if head or stop else "normal", color=WARN if stop else "black")
        y -= 0.028 if s else 0.012
    if note:
        fig.text(0.07, 0.04, note, fontsize=10, weight="bold", color=WARN)
    pdf.savefig(fig); plt.close(fig)



# ---------------------------------------------------------------- rope drawings (own simplified drawings)
def rope_line(ax, xs, ys, lw=7, z=3):
    ax.plot(xs, ys, color="#1d4f7a", lw=lw + 2.5, solid_capstyle="round", zorder=z)
    ax.plot(xs, ys, color=ROPE, lw=lw, solid_capstyle="round", zorder=z + 0.1)


def d_fig8(ax):
    """Figure-eight stopper knot in 4 steps (after Stanford build guide p. 12)."""
    ax.set_xlim(0, 20); ax.set_ylim(-2.3, 3.6); ax.set_aspect("equal"); ax.axis("off")
    t = np.linspace(0, 2 * np.pi, 200)
    for k, cap in enumerate(["1  loop: lay the end\nover the rope", "2  end around the\nrope, behind it",
                             "3  end down through\nthe first loop", "4  pull both sides:\nan \"8\" = done"]):
        x0 = 0.5 + k * 5
        if k == 0:
            rope_line(ax, [x0, x0 + 1.4], [0.6, 0.6]); rope_line(ax, x0 + 2.2 + 0.8 * np.cos(t[:170]), 1.2 + 0.8 * np.sin(t[:170]), z=4)
            rope_line(ax, [x0 + 2.9, x0 + 3.9], [1.6, 2.6], z=5)
        elif k in (1, 2):
            rope_line(ax, [x0, x0 + 1.4], [0.6, 0.6]); rope_line(ax, x0 + 2.2 + 0.8 * np.cos(t), 1.2 + 0.8 * np.sin(t), z=4)
            rope_line(ax, x0 + 2.2 + 0.55 * np.cos(t[40:190]), 0.0 + 0.55 * np.sin(t[40:190]), z=3 if k == 1 else 5)
            if k == 2:
                rope_line(ax, [x0 + 2.4, x0 + 3.9], [0.6, 2.9], z=6)
        else:
            rope_line(ax, x0 + 1.9 + 0.5 * np.sin(t), 0.9 + 0.75 * np.sin(2 * t) * 0.6, lw=6)
            rope_line(ax, [x0, x0 + 1.4], [0.9, 0.9]); rope_line(ax, [x0 + 2.4, x0 + 3.8], [0.9, 0.9])
            ax.annotate("", (x0 - 0.3, 0.9), (x0 + 0.4, 0.9), arrowprops=dict(arrowstyle="->", lw=2))
            ax.annotate("", (x0 + 4.2, 0.9), (x0 + 3.5, 0.9), arrowprops=dict(arrowstyle="->", lw=2))
        ax.text(x0 + 2.0, -1.0, cap, ha="center", va="top", fontsize=8.5)


def d_drum_tie(ax):
    """Drum cut through the tie hole: rope in through the hole, knot inside stops it, then wraps."""
    ax.set_xlim(-8.0, 8.5); ax.set_ylim(-3.4, 3.4); ax.set_aspect("equal"); ax.axis("off")
    ax.add_patch(Circle((0, 0), 1.9, fc=PRINT, ec="#9a7d0a", lw=1.5))              # core, rope surface d 38 mm
    ax.add_patch(Circle((0, 0), 1.3, fc="white", ec="#9a7d0a"))                     # hollow inside
    ax.add_patch(Circle((0, 0), 0.5, fc=STEEL, ec="#555"))                          # shaft
    ax.add_patch(Rectangle((-0.28, 1.25), 0.56, 0.75, fc="white", ec="#9a7d0a"))    # tie hole
    rope_line(ax, [0, 0, 3.5, 7.8], [0.95, 2.6, 2.6, 2.6], lw=5)
    ax.add_patch(Circle((0, 0.95), 0.33, fc=ROPE, ec="#1d4f7a", lw=2, zorder=8))     # the knot
    ax.annotate("figure-8 knot inside:\nit cannot pass the hole", (0, 0.95), (-7.8, 0.6), fontsize=9, arrowprops=dict(arrowstyle="->"))
    ax.annotate("tie hole (5.6 mm)", (0.3, 1.6), (2.0, 0.6), fontsize=9, arrowprops=dict(arrowstyle="->"))
    ax.annotate("rope to the load cell /\ndummy (via the eyebolt)", (7.0, 2.6), (4.6, -0.6), fontsize=9, arrowprops=dict(arrowstyle="->"))
    ax.text(0, -2.9, "drum, cut through the tie hole", ha="center", fontsize=9)


def rope_page(pdf):
    fig = plt.figure(figsize=A4)
    fig.text(0.07, 0.965, "Re-tie the rope on the drum", fontsize=16, weight="bold", va="top")
    fig.text(0.07, 0.938, "From Stanford's build guide (docs/reference/stanford-bumpem-build-guide.pdf p. 12, video \"Motor Unit |\n"
             "Reel Drum Rope Assembly\" on biomechatronics.stanford.edu/bump-em). Easiest with the drum OFF the shaft.",
             fontsize=9.5, va="top")
    lines = [
        "#1  Length",
        "• Rope length = W + 71 cm (28 in). W = how far the rope has to travel (e.g. the treadmill width).",
        "• At least 3 turns must stay on the drum when the rope is fully out.",
        "#2  Through the tie hole",
        "• Push the rope end from the OUTSIDE of the drum core into the small tie hole, so the end",
        "   comes out inside the core (picture below). Pull ~15 cm through.",
        "#3  Stopper knot (figure 8) on that end (pictures below)",
        "• Tie it close to the end, pull it tight, cut the tail to ~1 cm.",
        "• Pull the rope back: the knot jams inside and cannot come through the hole.",
        "#4  Wind it on",
        "• Drum back on the shaft (steps 7 on the previous page), then wind the rope on neatly side by",
        "   side, and out through the eyebolt in the cover.",
        "• Direction: do one 10 N test pull with the rope slack. The motor must WIND IT IN.",
        "   If it unwinds instead, take the turns off and wind them the other way round.",
        "#5  Other end",
        "• Stanford ties an overhand noose (a simple knot around the rope itself) to connect to the",
        "   breakaway cable / harness. Use the same connection as the other towers.",
    ]
    y = 0.885
    for s in lines:
        head = s.startswith("#"); s = s.lstrip("#")
        fig.text(0.07, y, s, fontsize=11 if head else 9.8, weight="bold" if head else "normal", va="top")
        y -= 0.024 + (0.004 if head else 0)
    ax = fig.add_axes([0.08, 0.275, 0.84, 0.20]); d_drum_tie(ax)
    ax2 = fig.add_axes([0.04, 0.02, 0.92, 0.21]); d_fig8(ax2)
    fig.text(0.07, 0.255, "Figure-8 stopper knot (good animations: search \"figure eight stopper knot\")", fontsize=11, weight="bold")
    pdf.savefig(fig); plt.close(fig)


if __name__ == "__main__":
    out = HERE / "disassembly-guide.pdf"
    with Pages(out) as pdf:
        photo_page(pdf)
        steps_page(pdf, "Take the drum off", [
            "#How the drum is held (Stanford build guide p. 11)",
            "drum  --3 bolts #6-32 x 1/2 in + #6 washers-->  flanged shaft collar  --its clamp-->  3/8 in shaft",
            "One of the 3 drum bolts is missing. Try first: a new bolt, no taking apart (last page).",
            "",
            "#0  Prepare",
            "• UI: Release (treadmill stopped). Stop the server. This tower's 48 V and 24 V OFF.",
            "• Take 4 photos (front, back, both sides). Put a cup or a magnetic tray next to you.",
            "• Marker: one line across drum hub (B), shaft and coupler (E), so it goes back the same way.",
            "",
            "#1  Free the rope",
            "• Unhook the rope from the load cell / dummy. Unwind it from the drum.",
            "• Keep it on the drum if you want: you re-tie it anyway (rope page).",
            "",
            "#2  Loosen the 3 drum bolts (B): 7/64 in hex key",
            "• Turn the drum until a hole faces you; key straight down the hole; counter-clockwise.",
            "",
            "#3  Loosen the coupler's drum-side clamp screw (E)",
            "• Small screw on top of the silver coupler half next to the black mount wall.",
            "   Stanford's tool list: 2.5 mm hex (try 7/64 in too). Two turns are enough.",
            "• Do NOT touch the motor-side half (G): it stays on the motor shaft.",
            "",
            "#4  Push the shaft out (3/8 in x 3 in steel rod, in 2 bearings)",
            "• The drum sits between the 2 bearings: the shaft has to slide out lengthwise.",
            "• Push one end with your thumb or a wooden/plastic rod, light taps, while holding the drum.",
            "   If it does not go one way, try the other way.",
            "!• It does not move with light taps? STOP and send photos of both shaft ends.",
            "!• Never hammer on the shaft or the printed parts.",
            "",
            "#5  Lay the parts out in order",
            "• Drum, collar, washers or spacers (note where they were), shaft. The red star (F) may fall",
            "   out of the coupler: put it back into the motor-side half (G).",
        ])
        steps_page(pdf, "Fix and put it back", [
            "#6  While it is apart",
            "• Shake the drum: the missing bolt may be inside. Get it out.",
            "• Buy 3 new #6-32 x 1/2 in socket head cap screws + 3 #6 washers (inch screws; or bring",
            "   one old bolt to the store as a sample).",
            "• Collar on the shaft: clean the shaft and the collar's bore (cloth + alcohol), no oil.",
            "• Re-tie the rope now, while the drum is off (next page).",
            "",
            "#7  Put it back (reverse order)",
            "• Drum + collar: 3 bolts with washers, a drop of blue threadlocker, tighten firmly (7/64 in).",
            "• Shaft through bearing, drum/collar and the other bearing, into the coupler half (E), as",
            "   deep as before (marker line). Keep ~1 mm gap at the red star: do not squeeze the claws.",
            "• Collar clamp screw: tighten firmly on the clean shaft. Coupler clamp screw (E): firmly.",
            "• Turn the drum by hand: it must not rub the mount or the cover.",
            "",
            "#8  Test (after 10 min for the threadlocker)",
            "• New marker line across drum, collar, shaft and coupler.",
            "• Rope on: at least 3 turns stay on the drum when tight.",
            "• 24 V + 48 V on, testing page: 10 N (does it wind IN?), then 30, 50, 100 N, 1000 ms each.",
            "• Line still straight and the pulls get stronger = fixed. Then check towers A, C, D too.",
            "",
            "#Without taking it apart (try this first)",
            "• Put a new #6-32 x 1/2 in bolt + washer into the empty hole (on the end of the 7/64 in key),",
            "   threadlocker, tighten all 3 bolts.",
        ], note="Labels on page 1 are read from one photo of tower B.\nIf your tower looks different, send a photo and the guide is updated.")
        rope_page(pdf)
    print("written", out)

"""Take the reel drum off a motor unit (and put it back), on the user's photo of tower B (2026-10-28).
Run: python disassembly_guide.py  ->  disassembly-guide.pdf (needs numpy, matplotlib, Pillow; PREVIEW=<dir> also writes PNGs)."""
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle
from PIL import Image, ImageOps

from slip_check_guide import A4, HERE, WARN, Pages

PHOTO = HERE / "photos/motor_unit_B_2026-10-28.jpg"
OK, NO = "#1f8a4c", WARN

# label: (text, point on the photo (x, y) in pixels of the upright 1200 x 1600 image, label position, colour)
LABELS = {
    "A": ("Reel drum (rope spool)", (290, 900), (60, 1350), OK),
    "B": ("Drum hub, 2 holes with screws inside\n= joint 3 (one screw missing)", (440, 745), (60, 600), WARN),
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


if __name__ == "__main__":
    out = HERE / "disassembly-guide.pdf"
    with Pages(out) as pdf:
        photo_page(pdf)
        steps_page(pdf, "Take the drum off", [
            "#Why: one screw in the drum hub (B) is missing; the drum slipped on the shaft.",
            "First try without taking it apart: a new screw through the empty hole (see last page).",
            "Only take the drum off if that does not work.",
            "",
            "#0  Prepare",
            "• UI: Release (treadmill stopped). Stop the server. This tower's 48 V and 24 V OFF.",
            "• Take 4 photos (front, back, both sides). Put a cup or a magnetic tray next to you.",
            "• Marker: one line across drum hub (B), shaft and coupler (E), so it goes back the same way.",
            "",
            "#1  Free the rope",
            "• Unhook the rope from the load cell / dummy. Unwind it from the drum.",
            "• The knot sits inside the drum core: push it out through the tie hole, or leave the rope",
            "   on and take drum + rope off together.",
            "",
            "#2  Loosen the drum hub screws (B)",
            "• Turn the drum until a hole faces you. Hex key: inch, 3/32\" or 7/64\" (whichever fits",
            "   with no wobble). Turn counter-clockwise until the screw is loose. Same for the other hole.",
            "• You do not have to take them out. The drum should now turn on the shaft by hand.",
            "",
            "#3  Loosen the coupler's drum-side clamp screw (E)",
            "• The small screw on top of the silver coupler half next to the black mount wall.",
            "   Size: try metric 2 / 2.5 mm and inch 3/32\" / 7/64\". Two turns are enough.",
            "• Do NOT touch the motor-side half (G): it stays on the motor shaft.",
            "",
            "#4  Pull the shaft out",
            "• Pull the drum (with the shaft inside) away from the mount, straight, twisting a little.",
            "   The shaft slides out of the coupler (E) and the bearing (C).",
            "• Or, if the shaft stays: slide the drum off the shaft end.",
            "!• It does not move with firm hand force? STOP. Something on the far side of the drum",
            "!   holds it (the big black disc, left of A). Send a photo of that side before going on.",
            "!• Never hammer: printed parts crack.",
            "",
            "#5  Lay the parts out in order",
            "• Drum, any washers or spacers (note where they were), shaft. The red star (F) may fall",
            "   out of the coupler: put it back into the motor-side half (G).",
        ])
        steps_page(pdf, "Fix and put it back", [
            "#6  While it is apart",
            "• Look at the shaft where the hub screws press: marks or a dent = where they slipped.",
            "• File a FLAT there (10 mm long, ~0.5 mm deep; shaft in a vise). Clean away all filings.",
            "• Shake the drum: the missing screw may be inside the hub. Get it out.",
            "• New screws: take the remaining hub screw to a hardware store as a sample (likely #8-32",
            "   or #10-32 set screw, cup point). Buy 3.",
            "",
            "#7  Put it back (reverse order)",
            "• Shaft through the bearing (C) into the coupler half (E), until it sits as deep as before",
            "   (marker line). Keep ~1 mm gap between the red star and the claws: do not squeeze them.",
            "• Tighten the coupler clamp screw (E) firmly.",
            "• Drum onto the shaft as before (marker line). Turn it: it must not rub the mount or cover.",
            "• Hub screws (B): one drop of blue threadlocker each, screw onto the FLAT, tighten firmly.",
            "",
            "#8  Test (after 10 min for the threadlocker)",
            "• New marker line across hub, shaft and coupler.",
            "• Rope back on: at least 3 turns stay on the drum when tight.",
            "• 24 V + 48 V on, testing page: 30 N, 50 N, 100 N, 1000 ms each.",
            "• Line still straight and the pulls get stronger = fixed. Then check towers A, C, D too.",
            "",
            "#Without taking it apart (try this first)",
            "• Take the remaining hub screw out, buy matching ones, drop a new screw into the empty",
            "   hole on the end of the hex key, threadlocker on both, tighten both.",
        ], note="Labels on page 1 are read from one photo of tower B.\nIf your tower looks different, send a photo and the guide is updated.")
    print("written", out)

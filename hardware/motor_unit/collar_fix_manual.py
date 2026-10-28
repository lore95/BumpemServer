"""Step-by-step manual: open the motor unit and stop the shaft collar slipping (joint 3 in slip-check-guide.pdf).
Run: python collar_fix_manual.py  ->  collar-fix-manual.pdf (needs numpy + matplotlib; PREVIEW=<dir> also writes PNGs)."""
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyBboxPatch, Polygon, Rectangle

from slip_check_guide import (A4, DARK, HERE, MARK, PRINT, ROPE, STEEL, WARN, Pages, collar, drivetrain, drum, number,
                              shaft)


def page(pdf, title, steps, draw=None, draw_rect=(0.06, 0.08, 0.88, 0.36), note=None):
    """Numbered steps at the top, an optional drawing below, an optional warning line at the bottom."""
    fig = plt.figure(figsize=A4)
    fig.text(0.07, 0.95, title, fontsize=17, weight="bold", va="top")
    y = 0.90
    for s in steps:
        head = s.startswith("#")
        s = s.lstrip("#")
        fig.text(0.07, y, s, fontsize=11.5 if head else 10.5, weight="bold" if head else "normal", va="top")
        y -= 0.026 * (s.count("\n") + 1) + (0.008 if head else 0.004)
    if draw:
        ax = fig.add_axes(draw_rect); ax.axis("off"); ax.set_aspect("equal")
        draw(ax)
    if note:
        fig.text(0.07, 0.04, note, fontsize=10.5, weight="bold", color=WARN, va="bottom")
    pdf.savefig(fig); plt.close(fig)


# ---------------------------------------------------------------- drawings
def d_tools(ax):
    ax.set_xlim(0, 10); ax.set_ylim(0, 4)
    items = [(0.8, "hex keys\n(metric AND inch)"), (2.9, "permanent\nmarker"), (4.9, "phone\n(photos)"),
             (6.9, "threadlocker\n(blue, medium)"), (8.9, "cloth +\nalcohol")]
    for x, t in items:
        ax.add_patch(FancyBboxPatch((x - 0.7, 1.5), 1.4, 1.6, boxstyle="round,pad=0.05", fc="#f2f2f2", ec="#999"))
        ax.text(x, 1.1, t, ha="center", va="top", fontsize=9)
    ax.plot([0.4, 1.2, 1.2], [2.0, 2.0, 2.8], color=DARK, lw=5, solid_capstyle="butt")             # hex key
    ax.add_patch(Rectangle((2.3, 2.2), 1.2, 0.3, fc=DARK)); ax.add_patch(Rectangle((3.5, 2.25), 0.2, 0.2, fc=WARN))
    ax.add_patch(FancyBboxPatch((4.55, 1.75), 0.7, 1.15, boxstyle="round,pad=0.03", fc=DARK))
    ax.add_patch(Rectangle((6.6, 1.8), 0.6, 0.9, fc="#2a6fdb")); ax.add_patch(Rectangle((6.75, 2.7), 0.3, 0.3, fc="#ddd"))
    ax.add_patch(Rectangle((8.5, 1.8), 0.8, 0.8, fc="#cfe8ff", ec="#88a"))


def d_cover(ax):
    """Drum inside its printed cover: back half (part of the mount) and the removable front half."""
    ax.set_xlim(-1, 9); ax.set_ylim(-3, 3.3)
    shaft(ax, -0.5, 7.5, 0); collar(ax, 2.0, 0); drum(ax, 2.85, 0)
    ax.add_patch(Rectangle((1.4, -2.1), 0.3, 4.2, fc=PRINT, ec="#9a7d0a"))                 # back of the cover (on the mount)
    ax.add_patch(Polygon([[1.7, 2.1], [5.0, 2.1], [5.0, -2.1], [1.7, -2.1], [1.7, -1.8], [4.7, -1.8], [4.7, 1.8], [1.7, 1.8]],
                         closed=True, fc=PRINT, ec="#9a7d0a", alpha=0.35))                  # removable cover half
    for yy in (1.95, -1.95):
        ax.add_patch(Rectangle((4.75, yy - 0.08), 0.6, 0.16, fc=DARK))                     # cover screws
    ax.text(5.5, 2.4, "cover screws\n(small, about #6-32)", fontsize=9)
    ax.text(3.3, 2.5, "cover half\n(take off)", fontsize=9, ha="center")
    ax.text(1.5, -2.6, "back of the cover\n(stays on the mount)", fontsize=9, ha="center")
    number(ax, 2.17, 1.0, 3)
    ax.text(0.2, 1.1, "collar\n(joint 3)", fontsize=9, ha="center")


def d_collar_types(ax):
    ax.set_xlim(0, 10); ax.set_ylim(-2.4, 2.6)
    for cx, kind in ((2.4, "clamp"), (7.4, "set")):
        ax.add_patch(Circle((cx, 0), 1.5, fc=STEEL, ec="#555", lw=1.5))
        ax.add_patch(Circle((cx, 0), 0.55, fc="white", ec="#555"))                         # shaft hole
        if kind == "clamp":
            ax.add_patch(Rectangle((cx - 0.06, 0.55), 0.12, 0.95, fc="white", ec="none"))  # the slit
            ax.add_patch(Rectangle((cx - 1.0, 0.9), 2.0, 0.28, fc=DARK))                   # screw across the slit
            ax.text(cx, -2.0, "CLAMP type: a slit, and a screw\nACROSS the slit (squeezes the ring)", ha="center", fontsize=9.5)
        else:
            ax.add_patch(Rectangle((cx - 0.14, 0.55), 0.28, 1.0, fc=DARK))                 # screw pointing to the centre
            ax.text(cx, -2.0, "SET-SCREW type: no slit, a small screw\npointing INTO the shaft", ha="center", fontsize=9.5)
    ax.text(5, 2.3, "Which one is yours? (seen from the end of the shaft)", ha="center", fontsize=11, weight="bold")


def d_flat(ax):
    ax.set_xlim(0, 10); ax.set_ylim(-2.2, 2.4)
    ax.add_patch(Circle((2.2, 0), 1.3, fc=STEEL, ec="#555"))
    ax.add_patch(Rectangle((1.4, 1.0), 1.6, 0.4, fc="white", ec="none")); ax.plot([1.4, 3.0], [1.0, 1.0], color="#555")
    ax.add_patch(Rectangle((2.05, 1.05), 0.3, 1.0, fc=DARK))
    ax.text(2.2, -1.8, "shaft end view: flat on top,\nset screw presses on the flat", ha="center", fontsize=9.5)
    shaft(ax, 4.6, 9.6, 0, 0.9); ax.add_patch(Rectangle((6.6, 0.33), 1.4, 0.12, fc="#7d838a"))
    ax.annotate("flat: about 10 mm long,\n0.5 mm deep, where the\nscrew lands", (7.3, 0.4), (6.0, 1.5), fontsize=9,
                arrowprops=dict(arrowstyle="->"))
    ax.text(7.1, -1.2, "shaft side view", ha="center", fontsize=9.5)


def d_reassembled(ax):
    ax.set_xlim(-0.6, 9.3); ax.set_ylim(-3.0, 2.6)
    drivetrain(ax, marks=True)
    ax.text(4.2, 1.9, "marker line straight after 30 / 50 / 100 N test pulls = fixed", ha="center", fontsize=10, weight="bold")


# ---------------------------------------------------------------- pages
if __name__ == "__main__":
    out = HERE / "collar-fix-manual.pdf"
    with Pages(out) as pdf:
        page(pdf, "Fix a slipping shaft collar (joint 3)", [
            "#What this fixes",
            "The silver collar that holds the printed drum turns on the steel drive shaft when the rope",
            "gets tight. The motor then spins faster but the rope stays loose.",
            "#Before you start",
            "1. In the UI: Release (treadmill stopped), then stop the server (Ctrl+C).",
            "2. Switch this tower's 48 V OFF (and the 24 V). Wait 1 minute.",
            "3. Take the rope off the dummy / load cell; tape the free rope end to the frame so it",
            "    cannot unwind into a tangle.",
            "4. Take PHOTOS of the motor unit from 3 sides. They show how it goes back together.",
            "#Tools",
        ], draw=d_tools, draw_rect=(0.06, 0.40, 0.88, 0.22),
             note="Stanford's parts are partly in INCH sizes (3/8 in shaft, #6-32 screws): have inch hex keys too.\n"
                  "If a key does not fit snugly, try the other set; a loose key strips the screw.")
        page(pdf, "Step 1  Open the drum cover", [
            "1. Find the printed cover around the drum. It has a back half (part of the motor mount,",
            "    stays) and a front half that comes off.",
            "2. Undo the small screws that hold the front half (about #6-32). Put every screw and nut",
            "    in a cup.",
            "3. Lift the front half off. Do not pull on the rope.",
            "4. You now see the drum and, on one side of it, the silver collar (joint 3).",
            "#Can you reach the collar's screw with a hex key?",
            "• YES: leave the drum on the shaft and go to step 2.",
            "• NO: loosen the collar's screw, slide drum + collar off the shaft together (note which way",
            "    they face, and any washers). Take a photo first.",
        ], draw=d_cover, draw_rect=(0.06, 0.06, 0.88, 0.38))
        page(pdf, "Step 2  Which collar do you have?", [
            "Look at the collar from the end of the shaft and compare with the pictures.",
            "The fix depends on the type.",
            "#While it is open, also check joint 4",
            "The collar's flat disc is screwed to the drum with small screws. Try each with the key:",
            "• tight: fine.   • turns but tightens: tighten it.   • spins and never gets tight: the plastic",
            "  is torn → longer screw with a nut through the drum, or reprint the drum (slip-check-guide p. 4).",
        ], draw=d_collar_types, draw_rect=(0.06, 0.25, 0.88, 0.42))
        page(pdf, "Step 3A  Clamp-type collar (slit + screw across)", [
            "1. Loosen the clamp screw two turns. Turn the collar: it should move freely on the shaft.",
            "2. Clean the shaft where the collar sits and the inside of the collar: cloth + alcohol.",
            "    Oil or grease here is the most common reason a clamp slips.",
            "3. Look at the slit with the screw loose. If its two sides already touch, the collar is worn",
            "    or too big for the shaft: it cannot clamp. Replace it (same size, 3/8 in bore).",
            "4. One drop of blue threadlocker on the screw thread.",
            "5. Put the collar back where it was (against the drum, same position as in your photo).",
            "6. Tighten firmly: hold the drum, turn the key until it is hard to turn. Short key end only,",
            "    no extension.",
            "7. Leave the threadlocker 10 minutes before the test.",
            "#Go to step 4.",
        ])
        page(pdf, "Step 3B  Set-screw collar (screw into the shaft)", [
            "1. Undo the set screw and take it out. Look at its tip: if it is flat or shiny, it only",
            "    polished the round shaft. That is why it slips.",
            "2. Look at the shaft under the screw: is there a FLAT (a filed, flat strip)?",
            "    • Yes: turn the collar so the screw lands on the flat.",
            "    • No: make one (picture). Slide the drum + collar off first, mark where the screw sits,",
            "      then file a flat strip ~10 mm long and ~0.5 mm deep with a small flat file.",
            "      Clean away all filings.",
            "3. Clean the shaft and the screw with alcohol.",
            "4. One drop of blue threadlocker on the set screw. Tighten it firmly onto the flat.",
            "5. If the collar has a second set screw, do the same with it (90° from the first is fine).",
            "#Go to step 4.",
        ], draw=d_flat, draw_rect=(0.06, 0.08, 0.88, 0.30))
        page(pdf, "Step 4  Close up and test", [
            "1. Turn the drum by hand: it must spin freely without scraping the cover.",
            "2. Put the cover half back, same screws. Tighten evenly, not with force (it is plastic).",
            "3. Draw a new marker line along shaft, collar and drum.",
            "4. Rope back on the load cell / dummy; leave at least 3 turns on the drum when it is tight.",
            "5. 24 V and 48 V on. Start the server in testing mode:",
            "    bumpem serve --board /dev/cu.usbmodem169222501 --testing --modules ABCD",
            "6. Testing page: this tower, 30 N for 1000 ms, then 50 N, then 100 N.",
            "7. After each pull: is the marker line still straight? Did the rope pull harder each time?",
            "#Result",
            "• Line straight, pulls get stronger: fixed. Tell Claude which tower and what you did.",
            "• Line broken again: send a photo of the collar (docs/hardware-photos/); next option is a",
            "  collar with two clamp screws or a pin through collar and shaft.",
            "• Do the marker-line check on the other three towers as well: same design, same risk.",
        ], draw=d_reassembled, draw_rect=(0.06, 0.06, 0.88, 0.32))
    print("written", out)

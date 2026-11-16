"""E-stop guide: one button stops all four 48 V supplies through a 24 V relay (fail-safe), step by step with drawings.
Sources: docs/knowledge/wiring.md (e-stop), Mean Well RSP-2000 datasheet p. 4 + p. 6 (CN501: pin 7 Remote ON-OFF,
pin 11 +5V-AUX, short = OFF; Hirose DF11-12DS housing, DF11-**SC terminals), the user's photos of the BACO boxes
(docs/hardware-photos/2026-11-16_estop-*). Proposal: to be checked by the lab technician before building.
Run: python scripts/estop_guide.py  ->  docs/estop-guide.pdf. Same style as install_guide.py. PREVIEW=<dir> writes PNGs."""
import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyBboxPatch, Polygon, Rectangle

sys.path.insert(0, str(Path(__file__).resolve().parent))
from install_guide import ACCENT, DARK, MUTED, OK, WARN, Pages as _Pages, axes, box, page, wrap  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "estop-guide.pdf"
PHOTOS = ROOT / "docs" / "hardware-photos"
RED, GREEN, YELLOW, GREY = "#d1242f", "#2da44e", "#e3b341", "#8c959f"
TOWERS = [("A", "left"), ("B", "front"), ("C", "right"), ("D", "back")]


class Pages(_Pages):
    def save(self, fig):
        self.n += 1
        fig.text(0.93, 0.025, f"{self.n}", fontsize=9, color=MUTED, ha="right")
        fig.text(0.07, 0.025, "Bump'em: e-stop guide (2026-11-16, proposal: technician checks before building)", fontsize=9, color=MUTED)
        self.pdf.savefig(fig)
        if self.preview:
            fig.savefig(Path(self.preview) / f"estop_{self.n}.png", dpi=70)
        plt.close(fig)


def text(fig, y, lines, size=10.5, width=100):
    for s in lines:
        head, warn = s.startswith("#"), s.startswith("!")
        s = wrap(s.lstrip("#!"), 80 if head else width - 12 if warn else width)
        fig.text(0.07, y, s, fontsize=11.5 if head else size, weight="bold" if head or warn else "normal",
                 color=WARN if warn else DARK, va="top")
        y -= 0.0165 * (s.count("\n") + 1) + (0.012 if head else 0.007)
    return y


def photo(fig, rect, name, caption):
    ax = fig.add_axes(rect)
    if (PHOTOS / name).is_file():                 # hardware-photos/ is local only (.gitignore)
        ax.imshow(plt.imread(PHOTOS / name))
    else:
        ax.text(0.5, 0.5, f"photo not on this computer:\n{name}", ha="center", va="center", fontsize=8, color=MUTED)
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_title(caption, fontsize=9, color=MUTED)
    return ax


# ---------------------------------------------------------------- drawing pieces
def switch(ax, x, y, closed, color=DARK, w=0.8):
    """Contact between (x, y) and (x + w, y): straight = closed, tilted = open."""
    for xx in (x, x + w):
        ax.add_patch(Circle((xx, y), 0.06, fc="white", ec=color, lw=1.5, zorder=3))
    ax.plot([x, x + w] if closed else [x, x + w * 0.92], [y, y] if closed else [y, y + 0.32], color=color, lw=2.2)


def coil(ax, x, y, on):
    ax.add_patch(Rectangle((x, y - 0.25), 0.9, 0.5, fc="#fff8c5" if on else "white", ec=DARK, lw=1.5))
    ax.text(x + 0.45, y, "coil\n" + ("ON" if on else "off"), ha="center", va="center", fontsize=8, weight="bold",
            color=OK if on else MUTED)


def wire(ax, pts, color=DARK, lw=1.6):
    ax.plot([p[0] for p in pts], [p[1] for p in pts], color=color, lw=lw, solid_capstyle="round")


def contact_block(ax, x, y, color, top, bottom, name):
    """BACO-style contact block seen from the front: white body, coloured slider, two screw terminals."""
    ax.add_patch(FancyBboxPatch((x, y), 0.9, 2.2, boxstyle="round,pad=0.03", fc="#f6f8fa", ec=GREY, lw=1.2))
    ax.add_patch(Rectangle((x - 0.08, y + 0.95), 1.06, 0.3, fc=color, ec=color))
    for yy, n in ((y + 1.75, top), (y + 0.4, bottom)):
        ax.add_patch(Circle((x + 0.45, yy), 0.2, fc="#d0d7de", ec=DARK, lw=1))
        ax.plot([x + 0.33, x + 0.57], [yy, yy], color=DARK, lw=1.2)
        ax.text(x + 0.45, yy + (0.36 if n == top else -0.36), n, ha="center", va="center", fontsize=9, weight="bold",
                color="white", bbox=dict(boxstyle="square,pad=0.15", fc=color, ec=color))
    ax.text(x + 0.45, y - 0.55, name, ha="center", va="top", fontsize=8.5)


def relay(ax, x, y):
    """Plug-in relay on its screw socket (Finder 55.34 on 94.74 style), terminals named, not to exact layout."""
    ax.add_patch(Rectangle((x, y), 3.0, 0.9, fc="#d0d7de", ec=DARK, lw=1.2))                 # socket
    ax.add_patch(FancyBboxPatch((x + 0.5, y + 0.9), 2.0, 1.5, boxstyle="round,pad=0.04", fc="#ddf4ff", ec=DARK, lw=1.2))
    ax.text(x + 1.5, y + 1.65, "relay\n24 V DC\n4 changeover", ha="center", va="center", fontsize=8)
    for i, t in enumerate(("11 12 14", "21 22 24", "31 32 34", "41 42 44", "A1  A2")):
        ax.text(x + 0.3 + i * 0.6, y + 0.45, t.replace(" ", "\n").replace("\n\n", "\n"), ha="center", va="center",
                fontsize=5.8, family="DejaVu Sans Mono")
    ax.text(x + 1.5, y - 0.2, "relay + screw socket (+ coil module clipped on A1/A2)", ha="center", va="top", fontsize=8.5)


def df11(ax, x, y, s=0.42, label=True):
    """Hirose DF11-12DS housing seen from the wire side: two rows, odd pins 1..11 / even pins 2..12; 7 and 11 used."""
    ax.add_patch(FancyBboxPatch((x, y), 6 * s + 0.1, 2 * s + 0.1, boxstyle="round,pad=0.03", fc="#f6f8fa", ec=DARK, lw=1.2))
    for i in range(6):
        for r, n in ((1, 2 * i + 1), (0, 2 * i + 2)):
            used = n in (7, 11)
            ax.add_patch(Rectangle((x + 0.08 + i * s, y + 0.08 + r * s), s - 0.06, s - 0.06,
                                   fc=YELLOW if used else "white", ec=DARK if used else GREY, lw=1))
            ax.text(x + 0.05 + i * s + s / 2, y + 0.05 + r * s + s / 2, str(n), ha="center", va="center", fontsize=7,
                    weight="bold" if used else "normal", color=DARK if used else MUTED)
    if label:
        ax.text(x + 3 * s, y - 0.2, "DF11-12DS housing, wire side\nyellow = pin 7 and pin 11", ha="center", va="top", fontsize=8.5)


def crimp(ax, x, y):
    ax.add_patch(Polygon([(x, y), (x + 0.9, y), (x + 1.05, y + 0.09), (x + 0.9, y + 0.18), (x, y + 0.18)], fc="#e3b341", ec=DARK))
    wire(ax, [(x - 0.8, y + 0.09), (x, y + 0.09)], color=RED, lw=2.5)
    ax.text(x + 0.1, y - 0.25, "DF11 crimp terminal\non the wire end", ha="center", va="top", fontsize=8.5)


# ---------------------------------------------------------------- pages
def p_overview(P):
    fig, y = page("E-stop: one button stops all four towers", [
        "#What it does",
        "One big red button. Pressed once, all four 48 V motor supplies switch off together and every rope goes slack. "
        "The same happens by itself if a cable breaks, a plug comes out or the 24 V fails: then it is safe too (fail-safe).",
        "#Why a relay",
        "The two yellow BACO boxes in the lab each hold 2 contacts: one box reaches only 2 of the 4 supplies, and an "
        "emergency stop must be one press. And a plain contact is not fail-safe: a cut wire means the button silently "
        "does nothing. So: one button holds a relay switched on; the relay's 4 contacts switch the 4 supplies.",
        "#How the supplies are switched",
        "Each Mean Well RSP-2000 has a small control socket, CN501. Pin 7 (Remote ON-OFF) joined to pin 11 (+5V-AUX) = "
        "output OFF; open = ON (datasheet p. 4 and p. 6). Only this 5 V signal is switched: low voltage, no 230 V work.",
    ])
    ax = axes(fig, (0.07, 0.33, 0.86, 0.3), 10, 5)
    box(ax, 0.1, 2.0, 1.7, 1.0, "red button\n(1 NC contact)", fc="#ffebe9", ec=RED, weight="bold")
    box(ax, 2.7, 2.0, 1.9, 1.0, "relay box\n24 V relay,\n4 contacts", fc="#ddf4ff", ec=ACCENT, weight="bold")
    box(ax, 0.1, 3.8, 1.7, 0.8, "24 V supply", size=9)
    wire(ax, [(0.95, 3.8), (0.95, 3.0)]); wire(ax, [(1.8, 2.5), (2.7, 2.5)])
    for i, (m, where) in enumerate(TOWERS):
        yy = 4.2 - i * 1.15
        box(ax, 6.2, yy - 0.4, 3.6, 0.8, f"tower {m} ({where}): 48 V supply\nCN501 pin 7 + pin 11", size=8.5)
        wire(ax, [(4.6, 2.5), (5.3, 2.5), (5.3, yy), (6.2, yy)])
        ax.text(5.6, yy + 0.12, "2 wires", fontsize=7, color=MUTED)
    fig.text(0.07, 0.31, "Button released: relay ON → its contacts open → all four supplies ON.\n"
                         "Button pressed, cable cut or 24 V gone: relay OFF → contacts close → all OFF.",
             fontsize=10.5, weight="bold", va="top")
    text(fig, 0.26, [
        "!Before building: show this guide to the lab technician. It is the safety circuit: they agree the design, choose "
        "the 24 V supply for the relay and check the relay suits the RSP-2000's Remote ON-OFF input.",
        "The GRAIL treadmill's own e-stop stays the first stop. This button only removes the rope tension.",
    ])
    P.save(fig)


def p_parts(P):
    fig, y = page("The parts", ["Your button (one of the two yellow BACO boxes) and what to add. Shop links: ask Claude."])
    photo(fig, (0.06, 0.64, 0.42, 0.22), "2026-11-16_estop-button-front.jpg", "your button (front)")
    photo(fig, (0.52, 0.64, 0.42, 0.22), "2026-11-16_estop-button-inside.jpg", "inside: 2 green NO blocks, marked 3-4")
    ax = axes(fig, (0.05, 0.31, 0.9, 0.31), 10, 6)
    contact_block(ax, 0.3, 3.0, GREEN, "3", "4", "have: green NO\ncloses on press")
    contact_block(ax, 2.3, 3.0, RED, "1", "2", "buy: red NC\nopens on press")
    relay(ax, 4.1, 3.4)
    df11(ax, 7.4, 4.0)
    crimp(ax, 8.0, 2.5)
    for i, (title, body) in enumerate([
            ("Cable", "2-core, 0.25 mm²: button → relay box,\nrelay box → each tower"),
            ("2-pin plug per tower", "locking, so a tower can be\nunplugged and moved"),
            ("Small box + cable glands", "for the relay and socket;\nlabels A, B, C, D on each pair")]):
        box(ax, 0.2 + i * 3.3, 0.3, 3.1, 1.3, f"{title}\n{body}", size=8.5)
    text(fig, 0.29, [
        "#Shopping list",
        "•  1 × BACO contact block NC (red, 1-2), same series as your green ones (compare the side label).",
        "•  1 × relay 24 V DC coil, 4 changeover contacts, gold-flashed contacts (the switched current is a few mA), e.g. "
        "Finder 55.34 (gold version), + screw socket (Finder 94.74) + coil module with diode and LED (Finder 99.02, 24 V).",
        "•  4 × Hirose DF11-12DS housing, 8 + spares × DF11-2428SC crimp terminals (24–28 AWG), a fine crimp tool (makerspace?).",
        "•  2-core 0.25 mm² cable (measure the runs in the lab), 4 locking 2-pin plugs, small box, cable glands, labels.",
    ], size=9.8)
    P.save(fig)


def p_how(P):
    fig, y = page("How it works", [
        "Read the two pictures left to right. Normal: the button's red NC contact is closed, current flows through the "
        "relay coil, the coil pulls its contacts OPEN, CN501 pin 7 and 11 are not joined: the supply runs.",
        "Pressed (or a wire cut, or no 24 V): no current in the coil, its contacts fall back CLOSED, pin 7 and 11 are "
        "joined: the supply switches its 48 V off. The 4 relay contacts do this for all 4 supplies at once.",
    ])
    for row, (title, pressed) in enumerate([("NORMAL: button released", False), ("STOP: button pressed / wire cut / no 24 V", True)]):
        ax = axes(fig, (0.07, 0.48 - row * 0.3, 0.86, 0.26), 10, 4)
        ax.text(0, 3.75, title, fontsize=12, weight="bold", color=WARN if pressed else OK)
        box(ax, 0, 1.6, 1.1, 0.9, "24 V\n+", size=9)
        wire(ax, [(1.1, 2.05), (1.6, 2.05)])
        switch(ax, 1.6, 2.05, closed=not pressed, color=RED)
        ax.text(2.0, 1.55, "button NC 1-2", ha="center", fontsize=8)
        wire(ax, [(2.4, 2.05), (3.0, 2.05)])
        coil(ax, 3.0, 2.05, on=not pressed)
        wire(ax, [(3.9, 2.05), (4.3, 2.05), (4.3, 1.1), (0.55, 1.1), (0.55, 1.6)], color=MUTED)
        ax.text(2.4, 0.8, "back to 24 V −", ha="center", fontsize=8, color=MUTED)
        ax.annotate("", xy=(5.6, 2.35), xytext=(4.0, 2.35), arrowprops=dict(arrowstyle="-|>", color=MUTED, lw=1.2, ls="--"))
        ax.text(4.8, 2.55, "pulls", fontsize=7.5, color=MUTED, ha="center")
        ax.text(6.0, 3.2, "relay contact (NC)", ha="center", fontsize=8)
        switch(ax, 5.6, 2.05, closed=pressed, color=ACCENT)
        wire(ax, [(5.6, 2.05), (5.6, 1.4), (6.4, 1.4)]); wire(ax, [(6.4, 2.05), (6.9, 2.05)])
        box(ax, 6.9, 1.2, 3.0, 1.3, "CN501 pin 7 + 11\n" + ("joined → 48 V OFF" if pressed else "open → 48 V ON"),
            fc="#ffebe9" if pressed else "#dafbe1", ec=WARN if pressed else OK, weight="bold", size=9)
        wire(ax, [(6.4, 1.4), (6.9, 1.4)])
        ax.text(8.4, 0.75, "× 4 (one per tower)", ha="center", fontsize=8, color=MUTED)
    text(fig, 0.13, [
        "Bonus: the 48 V can only come on while the 24 V is on: the start-up order you already follow (24 V before 48 V).",
        "After a stop: twist the red button to release it → 48 V back on. The Teensy then needs Arm again before any rope pulls.",
    ])
    P.save(fig)


def p_wiring(P):
    fig, y = page("The whole wiring", [
        "Terminal numbers are printed next to each screw on the socket. Contact n: n1 = common, n2 = NC (closed when the "
        "relay is off), n4 = NO (not used). Use ONLY n1 and n2. Keep each tower's pair separate: never join two towers' wires.",
    ])
    ax = axes(fig, (0.05, 0.25, 0.9, 0.58), 10, 9)
    box(ax, 0.1, 7.3, 2.0, 1.1, "24 V supply\n(technician\nchooses)", size=8.5)
    ax.text(2.2, 8.15, "+", fontsize=11, weight="bold"); ax.text(2.2, 7.45, "−", fontsize=11, weight="bold")
    box(ax, 0.1, 4.6, 2.0, 1.4, "red button\nNC block\nterminals 1, 2", fc="#ffebe9", ec=RED, size=8.5)
    wire(ax, [(2.1, 8.15), (2.6, 8.15), (2.6, 5.6), (2.1, 5.6)], color=RED)
    ax.text(2.7, 6.9, "+24 V → 1", fontsize=8, color=RED)
    wire(ax, [(2.1, 5.0), (3.4, 5.0), (3.4, 7.0), (3.9, 7.0)], color=RED)
    ax.text(2.4, 4.75, "2 → A1", fontsize=8, color=RED)
    wire(ax, [(2.1, 7.55), (3.2, 7.55), (3.2, 7.8), (3.9, 7.8)], color=DARK)
    ax.text(3.0, 8.0, "− → A2", fontsize=8)
    ax.add_patch(Rectangle((3.9, 0.6), 2.0, 7.6, fc="#ddf4ff", ec=ACCENT, lw=1.4))
    ax.text(4.9, 8.4, "relay socket", ha="center", fontsize=9.5, weight="bold", color=ACCENT)
    terms = [("A2", 7.8), ("A1", 7.0)] + [(f"{n}{k}", 6.0 - i * 1.45 - j * 0.5) for i, n in enumerate("1234") for j, k in enumerate("12")]
    for t, yy in terms:
        ax.add_patch(Circle((5.6, yy), 0.13, fc="#d0d7de", ec=DARK))
        ax.text(5.35, yy, t, ha="right", va="center", fontsize=8.5, family="DejaVu Sans Mono", weight="bold")
    for i, (m, where) in enumerate(TOWERS):
        y1, y2 = 6.0 - i * 1.45, 5.5 - i * 1.45
        col = [ACCENT, OK, "#8250df", "#bc4c00"][i]
        wire(ax, [(5.73, y1), (7.0, y1)], color=col); wire(ax, [(5.73, y2), (7.0, y2)], color=col)
        ax.add_patch(Rectangle((6.6, y2 - 0.15), 0.35, y1 - y2 + 0.3, fc="white", ec=DARK))
        box(ax, 7.4, y2 - 0.2, 2.5, 0.9, f"tower {m} ({where})\nCN501 pin 11 / pin 7", size=8)
        wire(ax, [(7.0, y1), (7.4, y1)], color=col); wire(ax, [(7.0, y2), (7.4, y2)], color=col)
        ax.text(6.25, y1 + 0.12, f"{m}", fontsize=8, weight="bold", color=col)
    ax.text(6.78, 0.75, "2-pin plug\nper tower", ha="center", fontsize=8, color=MUTED)
    text(fig, 0.22, [
        "#Wire list (tick each)",
        "□  24 V + → button 1     □  button 2 → relay A1     □  24 V − → relay A2     □  coil module on A1/A2",
        "□  11 + 12 → tower A     □  21 + 22 → tower B     □  31 + 32 → tower C     □  41 + 42 → tower D",
        "(each pair: relay socket → 2-pin plug → that tower's CN501 pin 7 + pin 11)",
        "Which wire of a pair goes to pin 7 or pin 11 does not matter (it is a plain contact). Label both ends of every pair.",
    ], size=9.6)
    P.save(fig)


def p_button(P):
    fig, y = page("Step 1: the button", [
        "Work on the bench, nothing connected. Use ONE of the two boxes; keep the other one and its blocks as spares.",
        "1.  Open the box (4 screws on the front). Unclip ONE green block (they snap off the base); keep it.",
        "2.  Clip the red NC block into the same place. The second green block can stay, but leave it unwired.",
        "3.  Bring the 2-core cable in through the side hole (cable gland) and screw its wires to the red block's 1 and 2. "
        "Unscrew the old red / black wires from the green blocks and tape their ends, or take them out.",
        "4.  Meter in beep mode on the cable's other end: button released → BEEPS; button pressed → silent. Twist to release → beeps again.",
        "5.  Close the box. Label the cable \"E-STOP → relay box\".",
    ])
    photo(fig, (0.08, 0.3, 0.4, 0.4), "2026-11-16_estop-button-inside.jpg", "as found: two green NO blocks (3-4)")
    ax = axes(fig, (0.53, 0.32, 0.42, 0.38), 5, 5)
    contact_block(ax, 0.6, 1.8, GREEN, "3", "4", "unclip (spare)")
    ax.annotate("", xy=(2.4, 2.9), xytext=(1.7, 2.9), arrowprops=dict(arrowstyle="-|>", color=MUTED, lw=1.5))
    contact_block(ax, 2.7, 1.8, RED, "1", "2", "clip in, wire 1 and 2")
    wire(ax, [(3.15, 3.95), (3.15, 4.6), (4.6, 4.6)], color=RED); wire(ax, [(3.15, 2.2), (4.3, 2.2), (4.3, 4.4), (4.6, 4.4)], color=DARK)
    ax.text(4.65, 4.5, "cable to\nrelay box", fontsize=8, va="center")
    P.save(fig)


def p_relay(P):
    fig, y = page("Step 2: the relay box", [
        "Bench, nothing powered.",
        "1.  Screw the socket into the small box. Push the relay into the socket, clip the coil module onto A1 / A2 (its LED shows the relay is powered).",
        "2.  Glands: one for the button cable, one for the 24 V cable, one per tower cable (or one big one for four).",
        "3.  Wire as on page 4: button 2 → A1, 24 V − → A2, 24 V + goes to button 1. Tower pairs on 11/12, 21/22, 31/32, 41/42.",
        "4.  Meter in beep mode, relay NOT powered: each tower pair (plug end) BEEPS (NC contacts closed).",
        "5.  Power the 24 V only (towers not plugged in): LED on, each tower pair is now silent. Press the button: LED off, every pair beeps. "
        "Release: silent again. Unplug the button cable: every pair beeps. Write the results on page 8.",
    ])
    ax = axes(fig, (0.1, 0.3, 0.8, 0.36), 10, 6)
    ax.add_patch(FancyBboxPatch((0.5, 0.6), 9.0, 5.0, boxstyle="round,pad=0.1", fc="#f6f8fa", ec=DARK, lw=1.4))
    relay(ax, 3.4, 2.4)
    for i, lab in enumerate(["button", "24 V", "A", "B", "C", "D"]):
        x = 1.0 + i * 1.6
        ax.add_patch(Rectangle((x, 0.35), 0.5, 0.35, fc="#d0d7de", ec=DARK))
        ax.text(x + 0.25, 0.05, lab, ha="center", va="top", fontsize=8.5, weight="bold")
    ax.text(5.0, 5.2, "small box, seen from above (glands along one side)", ha="center", fontsize=9, color=MUTED)
    P.save(fig)


def p_plug(P):
    fig, y = page("Step 3: the plug on each power supply", [
        "One DF11-12DS housing per tower, only 2 of its 12 places used: pin 7 and pin 11. Both are in the row that holds "
        "pin 1 (1, 3, 5, 7, 9, 11): counted from the 1 2 end, the 4th and the 6th place. The supply's label shows 1 2 at "
        "one end of CN501 and 11 12 at the other.",
        "0.  Before crimping: hold the empty housing against CN501 the way it plugs in, find the two places over pin 7 and "
        "pin 11, mark them with a pen.",
        "1.  Strip 2 mm, crimp a DF11 terminal on each wire of the tower's pair (fine crimp tool; tug test each one).",
        "2.  Push the terminals into places 7 and 11 until they click. Compare with the drawing, then with the supply's label.",
        "3.  Other end: the 2-pin plug, so the tower can be unplugged from the relay box.",
        "!Plug in and out only with the supply switched OFF and its mains plug pulled. If something is already plugged into "
        "CN501, stop: take a photo and ask (it can carry sense wires).",
        "!Never connect anything to the other pins (+5V-AUX and +12V-AUX are live outputs). Never join two towers' pairs.",
    ])
    ax = axes(fig, (0.1, 0.22, 0.8, 0.3), 10, 5)
    df11(ax, 0.5, 2.4, s=0.6)
    crimp(ax, 6.5, 3.2)
    ax.text(0.5, 4.5, "1 2 at this end", fontsize=8.5, color=MUTED); ax.text(3.0, 4.5, "11 12 at this end", fontsize=8.5, color=MUTED)
    ax.annotate("pin 7", xy=(2.65, 3.35), xytext=(2.0, 0.6), fontsize=9, weight="bold", color=WARN,
                arrowprops=dict(arrowstyle="->", color=WARN))
    ax.annotate("pin 11", xy=(3.85, 3.35), xytext=(3.8, 0.6), fontsize=9, weight="bold", color=WARN,
                arrowprops=dict(arrowstyle="->", color=WARN))
    P.save(fig)


def p_test(P):
    fig, y = page("Step 4: first test, then before every session", [
        "#First test (with the technician)",
        "1.  Towers plugged into the relay box, 24 V on (relay LED on), then 48 V on: every ESCON LED on.",
        "2.  Press the button → every ESCON LED off (all 4 towers). Twist to release → all back on.",
        "3.  Unplug the button cable → all off. Plug back → all on.",
        "4.  Know the one weak spot: a tower's OWN plug or cable (relay box → supply) unplugged = that tower stays ON. "
        "So: check every tower plug is locked before every session.",
        "5.  24 V off → all four 48 V off.",
        "#Before every session (30 s)",
        "Press → all four ESCON LEDs off → release → on. Tower plugs locked. If anything differs: nobody in the harness.",
    ])
    from matplotlib.patches import Rectangle as R
    ax = axes(fig, (0.07, 0.3, 0.86, 0.32), 10, 5)
    cols = ["Test", "A", "B", "C", "D", "OK?"]
    widths = [4.4, 1.0, 1.0, 1.0, 1.0, 1.4]
    rows = [["Relay box: pairs beep, relay off", "", "", "", "", ""],
            ["Button pressed → ESCON LED off", "", "", "", "", ""],
            ["Released → on again", "", "", "", "", ""],
            ["Button cable unplugged → off", "", "", "", "", ""],
            ["24 V off → off", "", "", "", "", ""],
            ["Date / by", "", "", "", "", ""]]
    xs = [0]
    for w in widths:
        xs.append(xs[-1] + w)
    for r, row in enumerate([cols] + rows):
        for c, t in enumerate(row):
            ax.add_patch(R((xs[c], 4.6 - r * 0.62), widths[c], 0.62, fc="#f6f8fa" if r == 0 else "white", ec=GREY))
            ax.text(xs[c] + 0.1, 4.6 - r * 0.62 + 0.31, t, va="center", fontsize=9, weight="bold" if r == 0 else "normal")
    text(fig, 0.24, ["Bring this page to Claude afterwards: docs/TODO.md and docs/STATUS.md get updated."])
    P.save(fig)


def main():
    P = Pages(OUT)
    for f in (p_overview, p_parts, p_how, p_wiring, p_button, p_relay, p_plug, p_test):
        f(P)
    P.close()
    print(f"{OUT} ({P.n} pages)")


if __name__ == "__main__":
    main()

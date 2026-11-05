"""Lab week guide (after 2026-11-05): what to do in the lab, day by day, with fill-in tables. From docs/TODO.md.
Run: python scripts/lab_week_guide.py  ->  docs/lab-week-guide.pdf. Same style as install_guide.py (matplotlib).
PREVIEW=<dir> also writes one PNG per page."""
import os
import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyBboxPatch, Rectangle

sys.path.insert(0, str(Path(__file__).resolve().parent))
from install_guide import ACCENT, DARK, MUTED, WARN, Pages as _Pages, arrow, box, page  # noqa: E402
from install_guide import axes as _axes  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "docs" / "lab-week-guide.pdf"
UPDATE = "BumpemUpdate_2026-11-05_1542.zip"
YELLOW = "#9a6700"


def axes(fig, rect, w=10, h=5):
    ax = _axes(fig, rect, w, h)
    ax.set_xlim(-0.4, w + 0.4)                # room for box padding and edge labels
    return ax


class Pages(_Pages):
    def save(self, fig):
        self.n += 1
        fig.text(0.93, 0.025, f"{self.n}", fontsize=9, color=MUTED, ha="right")
        fig.text(0.07, 0.025, "Bump'em: lab week guide (written 2026-11-05)", fontsize=9, color=MUTED)
        self.pdf.savefig(fig)
        if self.preview:
            fig.savefig(Path(self.preview) / f"week_{self.n}.png", dpi=70)
        plt.close(fig)


def table(ax, x, y, cols, rows, widths, h=0.55, size=8.5):
    """Fill-in table: header row + rows (strings; empty = to fill in by hand)."""
    xs = [x]
    for w in widths:
        xs.append(xs[-1] + w)
    for r, row in enumerate([cols] + rows):
        yy = y - r * h
        for c, txt in enumerate(row):
            ax.add_patch(Rectangle((xs[c], yy - h), widths[c], h, fc="#f6f8fa" if r == 0 else "white", ec="#8c959f", lw=0.8))
            ax.text(xs[c] + 0.08, yy - h / 2, txt, fontsize=size, va="center", weight="bold" if r == 0 else "normal")
    return y - (len(rows) + 1) * h


def checklist(fig, y, items, size=10.3):
    """□ items; '!' = red. Returns y below."""
    from install_guide import wrap
    for s in items:
        warn = s.startswith("!")
        s = wrap("□  " + s.lstrip("!"), 98)
        fig.text(0.07, y, s, fontsize=size, color=WARN if warn else DARK, va="top")
        y -= 0.0165 * (s.count("\n") + 1) + 0.007
    return y


# ---------------------------------------------------------------- pages
def p_week(P):
    fig, y = page("Back in the lab: your week", [
        "#Bring",
        f"•  the USB stick with  {UPDATE}  (in bumpemInstallation on the Mac; built 2026-11-05)",
        "•  this guide (fill in the tables by hand), the Mac with Claude, a meter, a pen",
        "#How to use it",
        "One page per day. Do the boxes in order; tick them. Fill in the grey tables and bring them (and the CSV files) back to Claude: start Claude with  /clear , then say \"I'm back from the lab\" and attach the files. Claude reads docs/STATUS.md and docs/TODO.md and knows the rest.",
        "!Nobody goes into the harness this week until the e-stop is wired and tested (day 5). Every test here runs with the ropes tied to a fixed point.",
    ])
    ax = axes(fig, (0.07, 0.45, 0.86, 0.22), 10, 4.0)
    days = [("Day 1", "Install update\nconnections,\nclocks, ropes,\nzero sensors"),
            ("Day 2", "Pull strength\nkff 3.5 test\n(ropes tied off)"),
            ("Day 3", "Vicon + gait\nleft belt,\ngait pattern\n(person walks,\nno harness)"),
            ("Day 4", "Test block\nstudy pages\nend to end\n(ropes tied off)"),
            ("Day 5", "Safety + office\ne-stop, electrician,\nquestions")]
    for i, (d, t) in enumerate(days):
        cx = i * 2.02
        box(ax, cx, 0.2, 1.85, 3.6, "", fc="#ddf4ff" if i < 4 else "#fff8c5", ec=ACCENT if i < 4 else YELLOW)
        ax.text(cx + 0.92, 3.3, d, ha="center", fontsize=12, weight="bold")
        ax.text(cx + 0.92, 1.8, t, ha="center", va="center", fontsize=7.6, color=DARK)
        if i < 4:
            arrow(ax, cx + 1.88, 2.0, cx + 2.0, 2.0)
    fig.text(0.07, 0.40, "Golden rules (every day)", fontsize=11.5, weight="bold", va="top")
    checklist(fig, 0.375, [
        "Stop the treadmill BEFORE Release or STOP: both drop the rope tension.",
        "No 230 V work: mains sides belong to the electrician. ESCON Studio: look / Upload only, never Download, Auto-tune or Store.",
        "D-Flow: look only, never start or play anything. Don't change ESET, firewall or Nexus settings.",
        "Before every Arm: no yellow \"Board differs from the saved defaults\" line on the test page (a Teensy reset = firmware values).",
        "Don't flash the Teensy. Don't type long commands on the lab PCs: only the double-click .bat files.",
    ])
    P.save(fig)


def p_day1a(P):
    fig, y = page("Day 1 morning: install, connections, clocks", [
        "#1. Install (D-Flow PC, about 5 min)",
        f"1.  Copy  {UPDATE}  from the USB stick to the PC. Right-click > Extract All.",
        "2.  Close the black Bump'em server window if it is open.",
        "3.  In the NEW unzipped folder: double-click  update.bat  > Y  > wait for  \"All packages OK\".",
        "4.  In the installed folder (C:\\Users\\operator\\BumpemLab): double-click  apply_calibration.bat  > it writes the gains A 1.013, B 2.075, C 0.953, D 0.998 into the settings.",
        "#2. Start and check the connections",
        "5.  Teensy on USB, Nexus open in Live mode. Double-click  start_server.bat . The page opens by itself.",
        "6.  The server now connects to the Teensy (COM3) and Vicon (192.168.1.60:801) by itself and retries every 5 s.",
        "    Look under the header of the page: a RED box = something is missing, with the reason.",
        "    •  \"Teensy COM3 not connected\": Device Manager > Ports (COM & LPT) > note the Teensy's COM number. If it is not COM3: right-click start_server.bat > Edit > change the line  set BOARD=COM3 > save > start again.",
        "    •  \"Vicon ... not connected\": Nexus in Live mode? Force plates on? Then wait 5 s.",
        "7.  No red box = both connected.",
    ])
    ax = axes(fig, (0.07, 0.08, 0.86, y - 0.10), 10, 6.5)
    ax.text(0, 6.2, "3. Clocks (fill in): open http://127.0.0.1:8000/ui/BumpemActivation.html , wait 10 s, read the line under Start", fontsize=9.5, weight="bold")
    ax.text(0, 5.75, "\"Clocks on this PC: Teensy ±… ms, drift … ppm · Vicon ±… ms, … frames lost · in sync ✓\"", fontsize=9, color=MUTED, family="DejaVu Sans Mono")
    table(ax, 0, 5.4, ["", "± (jitter) ms", "drift ppm", "frames lost", "in sync ✓ ?"],
          [["Teensy", "", "", "—", ""], ["Vicon", "", "", "", ""]], [1.6, 2.0, 2.0, 2.0, 2.0])
    ax.text(0, 3.3, "On the simulator it read Teensy ±0.02 ms, Vicon ±0.1 ms; the real USB / network will be worse.\n"
            "Not in sync? Write down the reason the line shows (e.g. \"jitter 3.1 ms > 2 ms\").", fontsize=9, color=MUTED, va="top")
    table(ax, 0, 2.1, ["Teensy COM port really is", "Problems / messages seen"], [["", ""], ["", ""]], [3.6, 6.0], h=0.6)
    P.save(fig)


def towers(ax, cx, cy):
    """Top view: treadmill (two belts), subject, towers A left, B front, C right, D back."""
    ax.add_patch(Rectangle((cx - 1.1, cy - 1.6), 1.05, 3.2, fc="#ddf4ff", ec=ACCENT))
    ax.add_patch(Rectangle((cx + 0.05, cy - 1.6), 1.05, 3.2, fc="#ddf4ff", ec=ACCENT))
    ax.text(cx - 0.57, cy - 1.35, "left belt", ha="center", fontsize=7.5, color=ACCENT)
    ax.text(cx + 0.57, cy - 1.35, "right belt", ha="center", fontsize=7.5, color=ACCENT)
    ax.add_patch(Circle((cx, cy), 0.28, fc="white", ec=DARK, lw=1.2))
    ax.annotate("", xy=(cx, cy + 0.75), xytext=(cx, cy + 0.3), arrowprops=dict(arrowstyle="-|>", color=DARK))
    ax.text(cx + 0.08, cy + 0.6, "faces front", fontsize=7, color=MUTED)
    for name, (dx, dy), where in (("B", (0, 2.6), "front 0°"), ("A", (-2.6, 0), "left +90°"),
                                  ("C", (2.6, 0), "right −90°"), ("D", (0, -2.6), "back 180°")):
        ax.add_patch(Rectangle((cx + dx - 0.3, cy + dy - 0.3), 0.6, 0.6, fc="#fff8c5", ec=YELLOW, lw=1.4))
        ax.text(cx + dx, cy + dy, name, ha="center", va="center", fontsize=11, weight="bold")
        ax.text(cx + dx, cy + dy + (0.45 if dy >= 0 else -0.5), where, ha="center", fontsize=7.5, color=MUTED)
        ax.plot([cx + dx * 0.88, cx + dx * 0.12], [cy + dy * 0.88, cy + dy * 0.12], color="#8c959f", lw=1, ls="--")


def p_day1b(P):
    fig, y = page("Day 1 afternoon: towers, ropes, zero", [
        "#4. Towers in place (they move as one unit now)",
        "•  Each tower at its side as in the picture, ropes horizontal at harness height. Mark each tower's feet on the floor with tape, so a moved tower goes back to the same angle.",
        "•  Cables not pulled at the plugs.",
        "#5. New ropes",
        "•  Pull each rope out as far as it can go: at least 3 turns stay on the drum. Look at each splice.",
        "#6. Rope paths B and C (power OFF: power strips off)",
        "•  Pull each rope slowly by hand, compare with A and D. B reached only 44–48 % of the target, C was stuck before. Feel for rubbing, a tight pulley, the rope off its groove. Note it below.",
        "#7. Zero the sensors (new ropes = new zero)",
        "1.  Power on, start_server.bat, test page (http://127.0.0.1:8000/ui/). Board DISARMED, ropes on, slack.",
        "2.  Board settings > Zero sensors > Save as default. The yellow \"differs\" line must disappear.",
    ])
    ax = axes(fig, (0.07, 0.07, 0.86, y - 0.09), 10, 7)
    towers(ax, 2.7, 3.6)
    table(ax, 5.8, 6.6, ["Tower", "Rope by hand", "Turns ok"], [["A", "", ""], ["B", "", ""], ["C", "", ""], ["D", "", ""]],
          [0.9, 2.2, 1.1], h=0.62)
    ax.text(5.8, 3.3, "Rope by hand: free / rubs / stiff\n(B and C compared with A and D)", fontsize=8.5, color=MUTED, va="top")
    table(ax, 5.8, 2.2, ["Zero done + saved at (time)"], [[""]], [4.2], h=0.6)
    P.save(fig)


def p_day2(P):
    fig, y = page("Day 2: pull strength (kff 3.5)", [
        "#Why",
        "With kff 2 the pulls reached only ~60 % of the target (A, D), less on B and C. kff 3.5 should give about 100 %. This test checks it, tower by tower.",
        "#Setup (nobody on the treadmill)",
        "•  Each rope tied to a solid anchor (strap round a frame part / post) at harness height, in the rope's normal direction but OUTSIDE the treadmill area where a person walks (days 3 and 4 use the same setup). Straight, just tight. Stand aside, out of the rope line.",
        "#Steps (test page, http://127.0.0.1:8000/ui/)",
        "1.  Board settings: Baseline 4 N, Feedforward gain (kff) 3.5 > Apply. Check the yellow line: it lists exactly what differs.",
        "2.  Arm. Record (top right, green > blue).",
        "3.  Direction: angle of one tower (A +90, B 0, C −90, D 180). Perturbation: Amplitude 10 N, Duration 400 ms > Perturb now, twice, 5 s apart. Then Amplitude 30 N, twice.",
        "4.  Next tower, same. (Target = baseline + amplitude = 14 N and 34 N, as test 3.)",
        "5.  Release… (treadmill is off) > Stop rec > the force CSV downloads; also click events. Copy both to the USB stick.",
        "6.  Noise: Arm, Record 20 s doing nothing, one 10 N pull, Release, Stop rec. Copy the files.",
        "!Anything wrong (a rope moves that should not, FAULT, a noise): STOP (Esc). Note it.",
    ])
    ax = axes(fig, (0.07, 0.07, 0.86, y - 0.09), 10, 5)
    ax.add_patch(Rectangle((0.2, 1.0), 0.7, 2.6, fc="#fff8c5", ec=YELLOW))
    ax.text(0.55, 3.75, "tower", ha="center", fontsize=8.5)
    ax.plot([0.9, 3.9], [2.6, 2.6], color=DARK, lw=2)
    ax.text(2.4, 2.75, "rope, horizontal", ha="center", fontsize=8, color=MUTED)
    ax.add_patch(Rectangle((3.9, 0.8), 0.35, 3.2, fc="#d0d7de", ec=DARK))
    ax.text(4.07, 4.15, "fixed anchor\n(off the treadmill)", ha="center", fontsize=8.5)
    ax.text(2.4, 2.25, "tied at harness height", ha="center", fontsize=8, color=MUTED)
    table(ax, 5.9, 4.6, ["Tower", "10 N ok?", "30 N ok?", "Notes"], [["A", "", "", ""], ["B", "", "", ""], ["C", "", "", ""], ["D", "", "", ""]],
          [0.9, 1.0, 1.0, 1.5], h=0.62)
    ax.text(5.9, 1.2, "Files: force + events CSV (pulls),\nforce + events CSV (noise)", fontsize=8.5, color=MUTED, va="top")
    P.save(fig)


def p_day3(P):
    fig, y = page("Day 3: Vicon, left belt, gait pattern", [
        "!The person walks on the treadmill but is NOT in the harness. Ropes tied off as on day 2.",
        "#1. Plates",
        "•  In Nexus (look only): plates zeroed before the session, as usual.",
        "•  Ground force plot (test page): stand on ONE belt. The line that rises is that belt's plate. Note its name below.",
        "#2. A short protocol",
        "1.  http://127.0.0.1:8000/ui/BumpemSetUp.html > Download template > open in Excel: one subject (made-up code, real mass), ONE block at a walking speed, then one at a running speed. Save as CSV. (Check: does Excel open it in columns? Note it.)",
        "2.  Import CSV > yellow Confirm each block > Start the study (opens BumpemActivation).",
        "3.  Left belt: pick the plate you found above.",
        "#3. Gait pattern (ropes tied off as day 2, not on the person)",
        "1.  Arm (recording starts). The person walks on the treadmill at block 1's speed, steadily.",
        "2.  Record gait pattern, 20 s. Write down what it shows (table). Same at the running speed (block 2): the page says when.",
        "3.  Release (treadmill stopped first) > Stop rec > copy force, events, Vicon CSVs.",
        "!Do NOT press Start today: the test block is day 4, with the ropes still tied off.",
    ])
    ax = axes(fig, (0.07, 0.07, 0.86, y - 0.09), 10, 5.6)
    table(ax, 0, 5.5, ["Left belt = plate", "Template opened in columns?"], [["", ""]], [4.0, 5.6], h=0.6)
    table(ax, 0, 4.0, ["Speed m/s", "Stride L / R ms", "Contact L / R ms", "Threshold L / R N", "Noise sd N", "Plates Hz"],
          [["", "", "", "", "", ""], ["", "", "", "", "", ""]], [1.2, 1.8, 1.9, 1.9, 1.4, 1.4], h=0.62)
    ax.text(0, 1.8, "Expected roughly: stride 0.6–1.2 s, contact 0.25 s (running) to 0.7 s (walking),\nthreshold 20–100 N, plates 1000 Hz.\n"
            "A message \"low thresholds unstable\" or \"too few strides\": write it down.", fontsize=8.8, color=MUTED, va="top")
    P.save(fig)


def flow(ax, y):
    steps = ["Arm\n(records)", "Record gait\npattern", "Start\nblock n", "block done", "next speed:\nnew gait pattern"]
    for i, s in enumerate(steps):
        box(ax, i * 2.0, y, 1.7, 1.0, s, fc="#ddf4ff" if i < 3 else "#f6f8fa", ec=ACCENT, size=8.5)
        if i < 4:
            arrow(ax, i * 2.0 + 1.72, y + 0.5, i * 2.0 + 1.98, y + 0.5)


def p_day4(P):
    fig, y = page("Day 4: test block end to end", [
        "!Ropes tied off as on day 2; the person walks but is NOT in the harness.",
        "#Why",
        "The whole study chain once, without risk: plates find the steps, the server times the pulls, the ropes pull into the fixed points. The recording then shows whether the pulls land at the set gait phase.",
        "#Steps",
        "1.  BumpemSetUp: one block, walking speed, 4 perturbations, directions 90 -90, intensity small (5 % body weight), phase 60 % stance, timing random 10–15 steps. Confirm > Start the study.",
        "2.  BumpemActivation: Arm > person walks > Record gait pattern > System delay stays 0 for now > Start block 1.",
        "3.  Watch: the \"P\" marks on the ground force plot, the counter \"1 / 4 perturbations\". The block ends by itself.",
        "4.  Release (treadmill stopped first) > Stop rec > copy force, events, Vicon CSVs.",
        "!The ropes stay tied to the anchors outside the walking area, never to the person. Nobody stands in a rope line.",
    ])
    ax = axes(fig, (0.07, 0.30, 0.86, y - 0.33), 10, 2.0)
    flow(ax, 0.5)
    fig.text(0.07, 0.27, "System delay (later, needs the harness = after day 5)", fontsize=11.5, weight="bold", va="top")
    from install_guide import wrap
    fig.text(0.07, 0.245, wrap("The pulls land a little late by the plates → PC → Teensy → rope delay. It is measured once with a person standing on the plates in the harness and one sharp small pull, recorded; Claude reads the delay from the files and you enter it in \"System delay\" next to Start. Only after the e-stop is wired and tested.", 100),
             fontsize=10.3, va="top", color=DARK)
    ax2 = axes(fig, (0.07, 0.06, 0.86, 0.12), 10, 1.5)
    table(ax2, 0, 1.4, ["Test block ran?", "Pulls seen (P marks)", "Messages / problems"], [["", "", ""]], [2.4, 2.8, 4.4], h=0.6)
    P.save(fig)


def p_day5(P):
    fig, y = page("Day 5: safety and office", [
        "#Before anyone is in the harness",
    ])
    y = checklist(fig, y, [
        "!E-stop parts: Hirose DF11-12DS housing + DF11 crimp terminals per 48 V supply (CN501) ordered / here?",
        "!Wire the e-stop: CN501 pin 7 + pin 11, one NO contact per 48 V supply (A, B, C, D) (knowledge/wiring.md).",
        "!Test it: 48 V on, press → every ESCON LED off; release → back on. Before every session from then on.",
        "Technician: can the e-stop be made fail-safe (a cut wire now means the button does nothing)?",
        "Electrician: hand over docs/electrician/power-requirements.pdf (breakers, RS-15-24 230 V cover, earth to tower B's chopper).",
        "Supervisor: electrical safety inspection (DGUV V3)? One power strip per tower, each on its own wall socket.",
        "Tower B's chopper → ESCON cable: replaced with 1.5 mm² + ferrules? (status unknown)",
    ])
    fig.text(0.07, y - 0.01, "Questions to ask (write the answers here)", fontsize=11.5, weight="bold", va="top")
    y = checklist(fig, y - 0.04, [
        "Walking, running or both in the study?",
        "The study's parameter list (subject + per block, units, limits): needed for BumpemSetUp.",
        "Vicon administrator: is there a free sync output on the Lock box (voltage, connector), may we use it? (optional hardware sync)",
        "Supervisor: may we ask Motek about controlling the treadmill from our app? (Claude drafts the email)",
        "Carrier board: is it in use (or still the breadboard)? Tell Claude.",
    ])
    ax = axes(fig, (0.07, 0.06, 0.86, y - 0.09), 10, 4)
    for i in range(6):
        ax.plot([0, 10], [3.6 - i * 0.65, 3.6 - i * 0.65], color="#d0d7de", lw=0.8)
    P.save(fig)


def p_back(P):
    fig, y = page("Back to Claude: what to bring", [
        "#Files (USB stick, from the lab PC's Downloads or C:\\Users\\operator\\BumpemLab\\BumpemServer\\Logs)",
        "•  Day 2: force + events CSVs of the kff 3.5 pulls; the noise recording",
        "•  Day 3: force, events, Vicon CSVs of the gait patterns",
        "•  Day 4: force, events, Vicon CSVs of the test block",
        "•  calibration_..._applied.txt (from apply_calibration.bat, next to the calibration CSV)",
        "•  photos of these filled-in pages",
        "#Start the session",
        "Type  /clear  (fresh start, uses far less of your limit), then for example:",
        "    \"I'm back from the lab. Read STATUS and TODO. Files from day 2–4 are in ~/Downloads/lab_week.\"",
        "Claude then: checks pull strength per tower (kff), the gait detection against the SLAP script, the test block timing, the clock numbers; updates TODO; next steps.",
        "#Pages (server running)",
        "•  Test page: http://127.0.0.1:8000/ui/        •  Calibration: …/ui/calibrate.html",
        "•  BumpemSetUp (protocol): …/ui/BumpemSetUp.html        •  BumpemActivation (study): …/ui/BumpemActivation.html",
        "#If something goes wrong",
        "•  Red box on a page: read it; it says what is missing (Teensy port, Vicon) and retries by itself.",
        "•  \"Board restarted\" / yellow \"differs\" line: Disconnect, Connect (saved defaults come back), check before Arm.",
        "•  A tower behaves strangely: STOP (Esc), treadmill already stopped, note what you saw, photo, bring it to Claude.",
        "•  update.bat stops: photo of the window text.",
    ])
    P.save(fig)


def main():
    P = Pages(OUT)
    for f in (p_week, p_day1a, p_day1b, p_day2, p_day3, p_day4, p_day5, p_back):
        f(P)
    P.close()
    print(f"{OUT} ({P.n} pages)")


if __name__ == "__main__":
    main()

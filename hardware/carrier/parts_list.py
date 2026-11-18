"""Parts list for soldering the carrier board v1, as built (D23: 1 MOhm in the D1-D4 places, R5-R8 empty), German and
English. Only what is still missing (2026-11-18: Phoenix cable plugs, ferrules, board screws are there; the first MSTB
board headers melted). Plus another project's breadboard power module.
Source: README.md (parts table), fab/bumpem-carrier-bom.csv, docs/makerspace-list.md.
Run: python parts_list.py  ->  fab/bumpem-carrier-teileliste-de.pdf + fab/bumpem-carrier-parts-list-en.pdf (A4, matplotlib)."""
import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "scripts"))
from install_guide import A4, DARK, MUTED, wrap  # noqa: E402

TEXT = {
    "de": dict(
        out="bumpem-carrier-teileliste-de.pdf",
        title="Trägerplatine Bump'em: Teileliste zum Löten",
        sub="Stand 18.11.2026 · nur was noch fehlt (Stecker, Aderendhülsen, Schrauben sind schon da)",
        cols=["☐", "Anz.", "Bauteil", "Platz"],
        rows=[
            ("4", "Widerstand 1 kΩ, 0,25 W, 1 %, axial", "R1–R4", "braun-schwarz-schwarz-BRAUN-braun; Richtung egal"),
            ("4", "Widerstand 1 MΩ, 0,25 W, 1 %, axial", "Plätze D1–D4", "braun-schwarz-schwarz-GELB-braun; statt der Dioden (keine BAT85); Richtung egal"),
            ("2", "Buchsenleiste 1 × 24, RM 2,54 mm, 8,5 mm hoch", "Teensy-Sockel", "oder aus Buchsenleiste 1 × 40 schneiden"),
            ("2", "Buchsenleiste 1 × 6, RM 2,54 mm", "DAC-Sockel", ""),
            ("4", "Phoenix Contact MSTB 2,5/5-GF-5,08 (1776537)", "J1–J4", "NEU: Grundleiste mit Gewindeflansch (alte geschmolzen); Öffnung zum Platinenrand"),
            ("1", "Breadboard-Netzteil-Modul MB102 (3,3 V / 5 V)", "anderes Projekt", "ANDERES PROJEKT (nicht Bump'em): steckt auf die Breadboard-Schienen, Jumper auf 5 V"),
            ("1", "Steckernetzteil 9 V DC, Hohlstecker 5,5 × 2,1 mm", "anderes Projekt", "ANDERES PROJEKT: Versorgung für das MB102 (6,5–12 V)"),
        ],
        important="Wichtig",
        notes=[
            "Auf die Platine kommen nur BUCHSEN (weiblich). Teensy und DAC haben schon Stifte und werden nie eingelötet.",
            "Plätze D1–D4: 1-MΩ-Widerstände statt Dioden, R5–R8 leer. So zeigt ein loses Kraftkabel ≈ 200 N → Motor aus + FAULT.",
            "Reihenfolge: Widerstände → Buchsenleisten → MSTB-Leisten. Danach prüfen ohne Teensy / DAC: 3V3 ↔ GND darf NICHT piepen.",
            "MSTB-Leisten (Kunststoff schmilzt!): Stecker beim Löten aufgesteckt lassen (hält die Stifte gerade), ca. 320–350 °C, "
            "pro Stift max. 2–3 s, Spitze nur an Pad + Stift, nie an den Kunststoff; zwischen den Stiften abkühlen lassen.",
            "Geschmolzene Leisten zuerst entfernen: Stifte einzeln mit Entlötpumpe / Entlötlitze freilegen, Löcher frei machen."],
        tools_title="Werkzeug mitbringen",
        tools=["Lötstation + Lötzinn 0,5–0,8 mm", "Flussmittel", "Entlötlitze + Entlötpumpe", "Seitenschneider",
               "Abisolierzange", "Crimpzange für Aderendhülsen", "Multimeter (Durchgangsprüfer)",
               "Lötanleitung: fab/bumpem-carrier-soldering.pdf", "Teensy und DAC (nur zum Anprobieren, nicht einlöten)"],
    ),
    "en": dict(
        out="bumpem-carrier-parts-list-en.pdf",
        title="Bump'em carrier board: parts list for soldering",
        sub="18 Nov 2026 · only what is still missing (cable plugs, ferrules, screws are already there)",
        cols=["☐", "Qty", "Part", "Goes to"],
        rows=[
            ("4", "Resistor 1 kΩ, 0.25 W, 1 %, axial", "R1–R4", "brown-black-black-BROWN-brown; either way round"),
            ("4", "Resistor 1 MΩ, 0.25 W, 1 %, axial", "D1–D4 places", "brown-black-black-YELLOW-brown; instead of the diodes (no BAT85); either way round"),
            ("2", "Female header 1 × 24, 2.54 mm pitch, 8.5 mm tall", "Teensy socket", "or cut from a 1 × 40 female header"),
            ("2", "Female header 1 × 6, 2.54 mm pitch", "DAC socket", ""),
            ("4", "Phoenix Contact MSTB 2,5/5-GF-5,08 (1776537)", "J1–J4", "NEW: board header with threaded flange (old ones melted); opening towards the board edge"),
            ("1", "Breadboard power module MB102 (3.3 V / 5 V)", "other project", "OTHER PROJECT (not Bump'em): plugs onto the breadboard rails, jumper on 5 V"),
            ("1", "Plug-in power supply 9 V DC, barrel plug 5.5 × 2.1 mm", "other project", "OTHER PROJECT: powers the MB102 (6.5–12 V)"),
        ],
        important="Important",
        notes=[
            "Only SOCKETS (female) go on the board. The Teensy and the DAC already have pins and are never soldered in.",
            "D1–D4 places: 1 MΩ resistors instead of diodes, R5–R8 empty. A loose force cable then reads ≈ 200 N → motor off + FAULT.",
            "Order: resistors → female headers → MSTB headers. Then check without Teensy / DAC: 3V3 ↔ GND must NOT beep.",
            "MSTB headers (the plastic melts!): keep the plug pushed on while soldering (holds the pins straight), about "
            "320–350 °C, max. 2–3 s per pin, tip only on pad + pin, never on the plastic; let it cool between pins.",
            "Remove the melted headers first: free each pin with a desoldering pump / wick, clear the holes."],
        tools_title="Bring these tools",
        tools=["Soldering station + solder 0.5–0.8 mm", "Flux", "Desoldering wick + pump", "Side cutters",
               "Wire stripper", "Ferrule crimper", "Multimeter (continuity beep)",
               "Soldering guide: fab/bumpem-carrier-soldering.pdf", "Teensy and DAC (only to test the fit, never soldered)"],
    ),
}


def make(t):
    fig = plt.figure(figsize=A4)
    fig.text(0.07, 0.955, t["title"], fontsize=17, weight="bold", va="top")
    fig.text(0.07, 0.915, t["sub"], fontsize=9.5, color=MUTED, va="top")
    ax = fig.add_axes((0.05, 0.43, 0.9, 0.46)); ax.axis("off"); ax.set_xlim(0, 10); ax.set_ylim(0, 11)
    widths, h = [0.45, 0.8, 5.6, 3.15], 0.92
    for r, row in enumerate([t["cols"]] + [("☐",) + x[:3] for x in t["rows"]]):     # note column dropped (user, 2026-11-18)
        x, y = 0, 11 - (r + 1) * h
        for c, s in enumerate(row):
            ax.add_patch(Rectangle((x, y), widths[c], h, fc="#f6f8fa" if r == 0 else "white", ec="#8c959f", lw=0.8))
            ax.text(x + 0.07, y + h / 2, wrap(s, {2: 58, 3: 30}.get(c, 10)), va="center", fontsize=8.2,
                    weight="bold" if r == 0 or c == 1 else "normal", color=DARK)
            x += widths[c]
    y = 0.89 - 0.46 * (len(t["rows"]) + 1) * h / 11 - 0.04      # just below the table
    fig.text(0.07, y, t["important"], fontsize=11.5, weight="bold", va="top"); y -= 0.025
    for s in t["notes"]:
        s = wrap("•  " + s, 100)
        fig.text(0.07, y, s, fontsize=9.5, va="top"); y -= 0.016 * (s.count("\n") + 1) + 0.006
    y -= 0.01
    fig.text(0.07, y, t["tools_title"], fontsize=11.5, weight="bold", va="top"); y -= 0.025
    for i, s in enumerate(t["tools"]):
        fig.text(0.07 + (i % 2) * 0.43, y - (i // 2) * 0.02, "☐  " + s, fontsize=9.3, va="top")
    fig.text(0.07, 0.025, "Bump'em · IBMS Hochschule Offenburg · hardware/carrier/parts_list.py", fontsize=8.5, color=MUTED)
    out = HERE / "fab" / t["out"]
    fig.savefig(out)
    plt.close(fig)
    print(out)


def main():
    for t in TEXT.values():
        make(t)


if __name__ == "__main__":
    main()

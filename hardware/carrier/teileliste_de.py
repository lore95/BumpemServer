"""German parts list for soldering the carrier board v1, as built (D23: 1 MOhm in the D1-D4 places, R5-R8 empty).
Source: README.md (parts table), fab/bumpem-carrier-bom.csv, docs/makerspace-list.md section 1.
Run: python teileliste_de.py  ->  fab/bumpem-carrier-teileliste-de.pdf (one A4 page, matplotlib)."""
import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "scripts"))
from install_guide import A4, DARK, MUTED, WARN, wrap  # noqa: E402

OUT = HERE / "fab" / "bumpem-carrier-teileliste-de.pdf"

ROWS = [  # Anzahl, Bauteil, Platz, Hinweis
    ("4", "Widerstand 1 kΩ, 0,25 W, 1 %, axial", "R1–R4", "braun-schwarz-schwarz-BRAUN-braun; Richtung egal"),
    ("4", "Widerstand 1 MΩ, 0,25 W, 1 %, axial", "Plätze D1–D4", "braun-schwarz-schwarz-GELB-braun; statt der Dioden (keine BAT85); Richtung egal"),
    ("–", "nichts", "R5–R8", "LEER lassen"),
    ("2", "Buchsenleiste 1 × 24, RM 2,54 mm, 8,5 mm hoch", "Teensy-Sockel", "oder aus Buchsenleiste 1 × 40 schneiden"),
    ("2", "Buchsenleiste 1 × 6, RM 2,54 mm", "DAC-Sockel", ""),
    ("4 + 2", "Phoenix Contact MSTB 2,5/5-GF-5,08 (1776537)", "J1–J4", "NEU: Grundleiste mit Gewindeflansch (alte geschmolzen), 2 Reserve; Öffnung zum Platinenrand"),
    ("–", "Phoenix MSTB 2,5/5-STF-5,08 (1778014)", "Modulkabel", "Stecker schon vorhanden: NICHT kaufen"),
    ("4", "Abstandsbolzen M3 + Schraube M3", "4 Ecklöcher", "Platine auf die gedruckte Trägerplatte"),
    ("–", "Aderendhülsen 0,5 mm²", "Modulkabel", "schon vorhanden: NICHT kaufen (20 nötig: 5 Adern × 4 Kabel)"),
    ("2", "Stiftleiste 1 × 24 (Hilfsmittel)", "–", "NICHT einlöten: hält die Buchsen beim Löten gerade"),
]
TOOLS = ["Lötstation + Lötzinn 0,5–0,8 mm", "Flussmittel", "Entlötlitze + Entlötpumpe",
         "Seitenschneider", "Abisolierzange", "Crimpzange für Aderendhülsen", "Multimeter (Durchgangsprüfer)",
         "Lötanleitung: fab/bumpem-carrier-soldering.pdf", "Teensy und DAC (nur zum Anprobieren, nicht einlöten)"]


def main():
    fig = plt.figure(figsize=A4)
    fig.text(0.07, 0.955, "Trägerplatine Bump'em: Teileliste zum Löten", fontsize=17, weight="bold", va="top")
    fig.text(0.07, 0.915, "Stand 18.11.2026 · Platine v1 · so wie gebaut (D23). Abhaken, was da ist; schon Gelötetes überspringen.",
             fontsize=9.5, color=MUTED, va="top")
    ax = fig.add_axes((0.05, 0.43, 0.9, 0.46)); ax.axis("off"); ax.set_xlim(0, 10); ax.set_ylim(0, 11)
    widths, h = [0.45, 0.7, 3.4, 1.35, 4.1], 0.92
    cols = ["☐", "Anz.", "Bauteil", "Platz", "Hinweis"]
    for r, row in enumerate([cols] + [("☐",) + x for x in ROWS]):
        x, y = 0, 11 - (r + 1) * h
        for c, t in enumerate(row):
            ax.add_patch(Rectangle((x, y), widths[c], h, fc="#f6f8fa" if r == 0 else "white", ec="#8c959f", lw=0.8))
            bad = r > 0 and ("LEER" in t or "NICHT" in t or "keine BAT85" in t or "NEU:" in t)
            ax.text(x + 0.07, y + h / 2, wrap(t, {2: 34, 3: 13, 4: 44}.get(c, 10)), va="center", fontsize=8.2,
                    weight="bold" if r == 0 or c == 1 else "normal", color=WARN if bad else DARK)
            x += widths[c]
    y = 0.42
    fig.text(0.07, y, "Wichtig", fontsize=11.5, weight="bold", va="top"); y -= 0.025
    for s in ["Auf die Platine kommen nur BUCHSEN (weiblich). Teensy und DAC haben schon Stifte und werden nie eingelötet.",
              "Plätze D1–D4: 1-MΩ-Widerstände statt Dioden, R5–R8 leer. So zeigt ein loses Kraftkabel ≈ 200 N → Motor aus + FAULT.",
              "Reihenfolge: Widerstände → Buchsenleisten → MSTB-Leisten. Danach prüfen ohne Teensy / DAC: 3V3 ↔ GND darf NICHT piepen.",
              "MSTB-Leisten (Kunststoff schmilzt!): Stecker beim Löten aufgesteckt lassen (hält die Stifte gerade), ca. 320–350 °C, "
              "pro Stift max. 2–3 s, Spitze nur an Pad + Stift, nie an den Kunststoff; zwischen den Stiften abkühlen lassen.",
              "Geschmolzene Leisten zuerst entfernen: Stifte einzeln mit Entlötpumpe / Entlötlitze freilegen, Löcher frei machen."]:
        s = wrap("•  " + s, 100)
        fig.text(0.07, y, s, fontsize=9.5, va="top"); y -= 0.016 * (s.count("\n") + 1) + 0.006
    y -= 0.01
    fig.text(0.07, y, "Werkzeug mitbringen", fontsize=11.5, weight="bold", va="top"); y -= 0.025
    for i, t in enumerate(TOOLS):
        fig.text(0.07 + (i % 2) * 0.43, y - (i // 2) * 0.02, "☐  " + t, fontsize=9.3, va="top")
    fig.text(0.07, 0.025, "Bump'em · IBMS Hochschule Offenburg · hardware/carrier/teileliste_de.py", fontsize=8.5, color=MUTED)
    fig.savefig(OUT)
    print(OUT)


if __name__ == "__main__":
    main()

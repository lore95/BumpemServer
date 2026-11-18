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
            ("4", "Widerstand 1 kΩ, 0,25 W, 1 %, axial", "R1–R4"),
            ("4", "Widerstand 1 MΩ, 0,25 W, 1 %, axial", "Plätze D1–D4"),
            ("2", "Buchsenleiste 1 × 24, RM 2,54 mm, 8,5 mm hoch", "Teensy-Sockel"),
            ("2", "Buchsenleiste 1 × 6, RM 2,54 mm", "DAC-Sockel"),
            ("4", "Phoenix Contact MSTB 2,5/5-GF-5,08 (1776537)", "J1–J4"),
            ("1", "Breadboard-Netzteil-Modul MB102 (3,3 V / 5 V)", "anderes Projekt"),
            ("1", "Steckernetzteil 9 V DC, Hohlstecker 5,5 × 2,1 mm", "anderes Projekt"),
        ],
    ),
    "en": dict(
        out="bumpem-carrier-parts-list-en.pdf",
        title="Bump'em carrier board: parts list for soldering",
        sub="18 Nov 2026 · only what is still missing (cable plugs, ferrules, screws are already there)",
        cols=["☐", "Qty", "Part", "Goes to"],
        rows=[
            ("4", "Resistor 1 kΩ, 0.25 W, 1 %, axial", "R1–R4"),
            ("4", "Resistor 1 MΩ, 0.25 W, 1 %, axial", "D1–D4 places"),
            ("2", "Female header 1 × 24, 2.54 mm pitch, 8.5 mm tall", "Teensy socket"),
            ("2", "Female header 1 × 6, 2.54 mm pitch", "DAC socket"),
            ("4", "Phoenix Contact MSTB 2,5/5-GF-5,08 (1776537)", "J1–J4"),
            ("1", "Breadboard power module MB102 (3.3 V / 5 V)", "other project"),
            ("1", "Plug-in power supply 9 V DC, barrel plug 5.5 × 2.1 mm", "other project"),
        ],
    ),
}


def make(t):
    fig = plt.figure(figsize=A4)
    fig.text(0.07, 0.955, t["title"], fontsize=17, weight="bold", va="top")
    fig.text(0.07, 0.915, t["sub"], fontsize=9.5, color=MUTED, va="top")
    ax = fig.add_axes((0.05, 0.43, 0.9, 0.46)); ax.axis("off"); ax.set_xlim(0, 10); ax.set_ylim(0, 11)
    widths, h = [0.45, 0.8, 5.6, 3.15], 0.92
    for r, row in enumerate([t["cols"]] + [("☐",) + x for x in t["rows"]]):
        x, y = 0, 11 - (r + 1) * h
        for c, s in enumerate(row):
            ax.add_patch(Rectangle((x, y), widths[c], h, fc="#f6f8fa" if r == 0 else "white", ec="#8c959f", lw=0.8))
            ax.text(x + 0.07, y + h / 2, wrap(s, {2: 58, 3: 30}.get(c, 10)), va="center", fontsize=8.2,
                    weight="bold" if r == 0 or c == 1 else "normal", color=DARK)
            x += widths[c]
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

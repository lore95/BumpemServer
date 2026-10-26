"""Picture of both sides of the milled carrier board, assembled, from fab/board.json (build_milled.sh writes it).
Run: python render_milled.py  ->  fab/bumpem-carrier-milled-sides.png"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyBboxPatch, Rectangle

HERE = Path(__file__).parent
D = json.loads((HERE / "fab/board.json").read_text())
W, H = 154.0, 96.0
FR4, CU, SOLDER = "#d9c89a", "#c8834a", "#c9ccd1"
FP = {f["ref"]: f for f in D["fps"]}
BANDS_1K = ["#7b4a1e", "#111", "#111", "#7b4a1e", "#7b4a1e"]
BANDS_1M = ["#7b4a1e", "#111", "#111", "#f2d21b", "#7b4a1e"]


def base(ax, title):
    ax.set_aspect("equal"); ax.set_axis_off()
    ax.add_patch(FancyBboxPatch((0, 0), W, H, boxstyle="round,pad=0,rounding_size=1.5", facecolor=FR4, edgecolor="#8a7a50", lw=1.5))
    ax.set_xlim(-3, W + 3); ax.set_ylim(H + 3, -6)
    ax.text(W / 2, -2.5, title, ha="center", va="bottom", fontsize=12, weight="bold")


def holes(ax, X):
    for f in D["fps"]:
        for p in f["pads"]:
            r = p["drill"] / 2 if p["drill"] else 0.5
            ax.add_patch(Circle((X(p["x"]), p["y"]), r, facecolor="#2b2b2b", edgecolor="none", zorder=6))


def bottom(ax):
    X = lambda x: W - x                                           # seen from below: left and right swap
    base(ax, "BOTTOM (copper / solder side), seen from below")
    for s in D["segs"]:
        if s["layer"] == "B.Cu":
            ax.plot([X(s["a"][0]), X(s["b"][0])], [s["a"][1], s["b"][1]], color=CU, lw=s.get("w", 0.6) * 4.9,
                    solid_capstyle="round", zorder=3)
    for f in D["fps"]:
        for p in f["pads"]:
            if not p["net"]:
                continue
            sx, sy = p["sx"], p["sy"]
            ax.add_patch(FancyBboxPatch((X(p["x"]) - sx / 2, p["y"] - sy / 2), sx, sy, boxstyle=f"round,pad=0,rounding_size={min(sx, sy) / 2}",
                                        facecolor=SOLDER, edgecolor="#8a8d92", lw=0.4, zorder=4))
    holes(ax, X)
    for m, ref in zip("ABCD", ["J1", "J2", "J3", "J4"]):
        ax.text(X(FP[ref]["x"] - 4.5), FP[ref]["y"] + 0.2, m, color=CU, fontsize=11, weight="bold", ha="center", va="center", zorder=5)
    ax.text(X(38.5), 59.5, "Bump'em v2\nsolder side", color=CU, fontsize=6, ha="center", va="center", weight="bold", zorder=5)


def top(ax):
    X = lambda x: x
    base(ax, "TOP (parts side), assembled")
    holes(ax, X)
    # Teensy socket strips + Teensy outline (dashed: it plugs in last)
    for ref, h in (("U1", 2.5), ("U2", 2.5)):
        f = FP[ref]
        rows = sorted({round(p["y"], 2) for p in f["pads"]})
        xs = [p["x"] for p in f["pads"]]
        for y in rows:
            ax.add_patch(Rectangle((min(xs) - 1.27, y - h / 2), max(xs) - min(xs) + 2.54, h, facecolor="#222", zorder=7))
            for p in f["pads"]:
                if abs(p["y"] - y) < 0.1:
                    ax.add_patch(Rectangle((p["x"] - 0.5, y - 0.5), 1.0, 1.0, facecolor="#666", zorder=8))
        bx, by, bw, bh = f["bbox"]
        ax.add_patch(Rectangle((bx, by), bw, bh, fill=False, ls="--", ec="#1f6f3f", lw=1.0, zorder=9))
        ax.text(bx + bw / 2, by + bh / 2, "Teensy 4.1 plugs in here\n(USB at the left edge)" if ref == "U1" else "DAC (MCP4728)\nplugs in here",
                ha="center", va="center", fontsize=7, color="#1f6f3f", zorder=9)
    # wire links (insulated wire)
    for f in D["fps"]:
        if f["ref"].startswith("W"):
            a, b = f["pads"]
            ax.plot([a["x"], b["x"]], [a["y"], b["y"]], color="#e07b00", lw=3.2, solid_capstyle="round", zorder=10)
            ax.text((a["x"] + b["x"]) / 2 + 1.3, (a["y"] + b["y"]) / 2, f["ref"], fontsize=6.5, color="#a65400", weight="bold", zorder=11)
    # resistors
    for f in D["fps"]:
        if f["ref"].startswith("R"):
            a, b = f["pads"]
            vertical = abs(a["x"] - b["x"]) < 0.1
            ax.plot([a["x"], b["x"]], [a["y"], b["y"]], color="#9aa0a6", lw=1.2, zorder=10)
            cx, cy = (a["x"] + b["x"]) / 2, (a["y"] + b["y"]) / 2
            w_, h_ = (2.5, 6.3) if vertical else (6.3, 2.5)
            ax.add_patch(FancyBboxPatch((cx - w_ / 2, cy - h_ / 2), w_, h_, boxstyle="round,pad=0,rounding_size=1.0",
                                        facecolor="#7fb3e0", edgecolor="#4a6f8f", lw=0.6, zorder=11))
            bands = BANDS_1K if f["value"].startswith("1k") else BANDS_1M
            for i, c in enumerate(bands):
                t = -2.3 + i * 0.95 if i < 4 else 2.3
                if vertical:
                    ax.add_patch(Rectangle((cx - 1.25, cy + t - 0.22), 2.5, 0.44, color=c, zorder=12))
                else:
                    ax.add_patch(Rectangle((cx + t - 0.22, cy - 1.25), 0.44, 2.5, color=c, zorder=12))
            ax.text(cx + (2.0 if vertical else 0), cy + (0 if vertical else -2.2), f"{f['ref']} {f['value']}", fontsize=6,
                    ha="left" if vertical else "center", va="center" if vertical else "bottom", zorder=12)
    # plugs
    for ref, m in zip(["J1", "J2", "J3", "J4"], "ABCD"):
        f = FP[ref]; x0, y0 = f["x"], f["y"]
        ax.add_patch(Rectangle((x0 - 7.8, y0 - 2.4), 35.7, 10.5, facecolor="#3a8f3a", edgecolor="#1d5c1d", lw=0.8, zorder=10))
        for i in range(5):
            ax.add_patch(Rectangle((x0 + 5.08 * i - 1.8, y0 + 3.5), 3.6, 4.6, facecolor="#1d4f1d", zorder=11))
        for fx in (x0 - 5.5, x0 + 25.8):
            ax.add_patch(Circle((fx, y0 + 4.5), 1.3, facecolor="#c0c0c0", edgecolor="#555", zorder=11))
        ax.text(x0 + 10.16, y0 - 0.2, f"module {m}", ha="center", va="center", fontsize=7.5, color="white", weight="bold", zorder=12)
    for f in D["fps"]:
        if f["ref"].startswith("H"):
            ax.add_patch(Circle((f["x"], f["y"]), 1.6, facecolor="white", edgecolor="#555", zorder=7))


if __name__ == "__main__":
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(11, 14.5))
    top(a1); bottom(a2)
    fig.tight_layout()
    out = HERE / "fab/bumpem-carrier-milled-sides.png"
    fig.savefig(out, dpi=130, facecolor="white")
    print("written", out)

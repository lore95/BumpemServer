"""Connectivity check for the milled board: every net must be one piece of copper, counting each wire link (W1, W2 ...)
as a connection between its two pads. KiCad's DRC cannot know that, so it lists every wire link as 'unconnected'.
Run with KiCad's Python:  $KPY check_milled.py bumpem-carrier-milled.kicad_pcb"""
import math
import sys

import pcbnew

b = pcbnew.LoadBoard(sys.argv[1])
mm = pcbnew.ToMM

def seg_dist(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / L))
    return math.hypot(px - x1 - t * dx, py - y1 - t * dy)

items = []        # (net, kind, geometry)
for fp in b.GetFootprints():
    for p in fp.Pads():
        if p.GetNetname():
            c = p.GetPosition()
            items.append((p.GetNetname(), "pad", (mm(c.x), mm(c.y), mm(min(p.GetSize().x, p.GetSize().y)) / 2,
                          mm(max(p.GetSize().x, p.GetSize().y)) / 2), f"{fp.GetReference()}.{p.GetNumber()}"))
for t in b.GetTracks():
    items.append((t.GetNetname(), "trk", (mm(t.GetStart().x), mm(t.GetStart().y), mm(t.GetEnd().x), mm(t.GetEnd().y), mm(t.GetWidth()) / 2), ""))

parent = list(range(len(items)))
def find(i):
    while parent[i] != i:
        parent[i] = parent[parent[i]]; i = parent[i]
    return i
def union(i, j):
    parent[find(i)] = find(j)

def touches(a, b_):
    (_, ka, ga, _), (_, kb, gb, _) = a, b_
    if ka == "pad" and kb == "pad":
        return False
    if ka == "pad":
        a, b_, (ka, ga), (kb, gb) = b_, a, (kb, gb), (ka, ga)
    x1, y1, x2, y2, hw = ga
    if kb == "pad":
        px, py, r, R = gb
        return min(math.hypot(x1 - px, y1 - py), math.hypot(x2 - px, y2 - py)) <= R + 1e-3
    u1, v1, u2, v2, hw2 = gb
    return min(seg_dist(x1, y1, u1, v1, u2, v2), seg_dist(x2, y2, u1, v1, u2, v2),
               seg_dist(u1, v1, x1, y1, x2, y2), seg_dist(u2, v2, x1, y1, x2, y2)) <= max(hw, hw2) + 1e-3

for i in range(len(items)):
    for j in range(i + 1, len(items)):
        if items[i][0] == items[j][0] and touches(items[i], items[j]):
            union(i, j)
# wire links: footprint W* joins its two pads
for fp in b.GetFootprints():
    if fp.GetReference().startswith("W"):
        idx = [k for k, it in enumerate(items) if it[3].startswith(fp.GetReference() + ".")]
        union(idx[0], idx[1])

bad = 0
nets = sorted({it[0] for it in items})
for n in nets:
    pads = [k for k, it in enumerate(items) if it[0] == n and it[1] == "pad"]
    groups = {}
    for k in pads:
        groups.setdefault(find(k), []).append(items[k][3])
    if len(groups) > 1:
        bad += 1
        print(f"NOT CONNECTED  {n}: " + "  |  ".join(", ".join(g) for g in groups.values()))
links = sum(1 for fp in b.GetFootprints() if fp.GetReference().startswith("W"))
print(f"{len(nets)} nets, {links} wire links, {'all connected' if not bad else str(bad) + ' nets broken'}")
sys.exit(1 if bad else 0)

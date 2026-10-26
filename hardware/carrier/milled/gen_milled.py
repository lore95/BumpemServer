"""Carrier board, makerspace version: single-sided (all copper on B.Cu), no plating, no solder mask, no copper fill.
Same board outline, mounting holes, Teensy / DAC / plug positions as ../gen_carrier.py (the printed carrier plate fits).
Everything is soldered on the bottom. Where two tracks must cross, a wire link (W1, W2 ...) goes on the top side.
Unused socket pins are bare holes (no copper): nothing to solder, nothing to short (VIN cannot touch anything).
Force inputs as built on v1 (D23): 1 kOhm in series, 1 MOhm pull-up to 3.3 V (here on the plug side), no pull-down, no diode.

Run with KiCad's Python (8.x):
  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3 gen_milled.py
Writes bumpem-carrier-milled.kicad_pcb next to this file. Then ./build_milled.sh for DRC + fab files.
"""
import heapq
import math
import os
import random
import sys

import pcbnew
import wx

_app = wx.App(False)
HERE = os.path.dirname(os.path.abspath(__file__))
KFP = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/"
OUT = os.path.join(HERE, "bumpem-carrier-milled.kicad_pcb")

W, H = 154.0, 96.0
TW, GW, PW = 0.6, 1.0, 0.8          # track widths: signal, ground, 3.3 V
CL = 0.6                            # copper to copper
CL_USED = 0.8                       # extra room around soldered pads (solder spreads on bare copper)
CL_HOLE = 0.35                      # copper to a bare (unplated, unsoldered) hole
CL_EDGE = 0.8
PAD_SOCKET, PAD_R, PAD_LINK = 1.7, 2.0, 2.0
G = 0.635                           # routing grid: quarter of 2.54 mm
OX = 2.29 - 3 * G                   # grid aligned to the Teensy pin columns (and the gaps between them)
OY = 0.0

mm = pcbnew.FromMM
def P(x, y):
    return pcbnew.VECTOR2I(mm(x), mm(y))

board = pcbnew.BOARD()
ds = board.GetDesignSettings()
ds.SetCopperLayerCount(2)
nc = ds.m_NetSettings.m_DefaultNetClass
nc.SetClearance(mm(CL)); nc.SetTrackWidth(mm(TW))
ds.m_MinClearance = mm(0.5); ds.m_TrackMinWidth = mm(0.4); ds.m_CopperEdgeClearance = mm(0.5)
ds.m_MinThroughDrill = mm(0.6); ds.m_HoleClearance = mm(0.3)

NETS = {}
def net(name):
    if name not in NETS:
        n = pcbnew.NETINFO_ITEM(board, name, len(NETS) + 1); board.Add(n); NETS[name] = n
    return NETS[name]

def bottom_only(pad):
    ls = pcbnew.LSET(); ls.AddLayer(pcbnew.B_Cu); ls.AddLayer(pcbnew.B_Mask)
    pad.SetLayerSet(ls)

def bare_hole(fp, num, x, y, d=1.0):
    pad = pcbnew.PAD(fp)
    pad.SetAttribute(pcbnew.PAD_ATTRIB_NPTH); pad.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
    pad.SetSize(P(d, d)); pad.SetDrillSize(P(d, d)); pad.SetLayerSet(pad.UnplatedHoleMask())
    pad.SetNumber(""); pad.SetFPRelativePosition(P(x, y)); fp.Add(pad)

def copper_pad(fp, num, x, y, d, netname, square=False):
    pad = pcbnew.PAD(fp)
    pad.SetAttribute(pcbnew.PAD_ATTRIB_PTH); pad.SetShape(pcbnew.PAD_SHAPE_RECT if square else pcbnew.PAD_SHAPE_CIRCLE)
    pad.SetSize(P(d, d)); pad.SetDrillSize(P(1.0, 1.0)); pad.SetNumber(str(num)); bottom_only(pad)
    pad.SetFPRelativePosition(P(x, y)); fp.Add(pad)
    return pad

def outline(fp, x1, y1, x2, y2, layer=pcbnew.F_Fab, w=0.12):
    for a, b in (((x1, y1), (x2, y1)), ((x2, y1), (x2, y2)), ((x2, y2), (x1, y2)), ((x1, y2), (x1, y1))):
        s = pcbnew.PCB_SHAPE(fp); s.SetShape(pcbnew.SHAPE_T_SEGMENT); s.SetStart(P(*a)); s.SetEnd(P(*b))
        s.SetLayer(layer); s.SetWidth(mm(w)); fp.Add(s)

PADS = []      # (x, y, r, net, used) after placement; capsule pads as (x1, y1, x2, y2, r, net)
HOLES = []     # (x, y, r) bare holes
BODIES = []    # top-side part bodies (no wire link may cross them): (x1, y1, x2, y2)

def register(fp, used=True):
    for p in fp.Pads():
        c = p.GetPosition(); x, y = pcbnew.ToMM(c.x), pcbnew.ToMM(c.y)
        if p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
            HOLES.append((x, y, pcbnew.ToMM(p.GetDrillSize().x) / 2)); continue
        sx, sy = pcbnew.ToMM(p.GetSize().x), pcbnew.ToMM(p.GetSize().y)
        r = min(sx, sy) / 2; half = (max(sx, sy) - min(sx, sy)) / 2
        if sy > sx:
            PADS.append((x, y - half, x, y + half, r, p.GetNetname()))
        else:
            PADS.append((x - half, y, x + half, y, r, p.GetNetname()))

# ---------------------------------------------------------------- Teensy 4.1 socket (same pin map as gen_carrier.py)
T_NEAR = ["GND"] + [str(i) for i in range(13)] + ["3V3"] + [str(i) for i in range(24, 33)]                 # pads 1..24, x left->right
T_FAR = ["VIN", "GND", "3V3"] + [str(i) for i in range(23, 12, -1)] + ["GND"] + [str(i) for i in range(41, 32, -1)]  # pads 48..25
T_USED = {("n", "GND"): "GND", ("n", "3V3"): "+3V3", ("n", "27"): "EN_A", ("n", "28"): "EN_B", ("n", "29"): "EN_C", ("n", "30"): "EN_D",
          ("f", "19"): "SCL", ("f", "18"): "SDA", ("f", "17"): "F_D", ("f", "16"): "F_C", ("f", "15"): "F_B", ("f", "14"): "F_A"}
TX, TY = 31.5, 14.0
teensy = pcbnew.FOOTPRINT(board); teensy.SetReference("U1"); teensy.SetValue("Teensy 4.1 (socket)")
teensy.SetFPID(pcbnew.LIB_ID("bumpem-carrier-milled", "Teensy41_Socket_SingleSided"))
T_PIN = {}
for row, names, ry, num0 in (("n", T_NEAR, 7.62, 1), ("f", T_FAR, -7.62, 48)):
    for i, nm in enumerate(names):
        x = -29.21 + 2.54 * i; num = num0 + i if row == "n" else num0 - i
        n = T_USED.get((row, nm))
        if n:
            copper_pad(teensy, num, x, ry, PAD_SOCKET, n, square=(num == 1)); T_PIN[(row, nm)] = (TX + x, TY + ry)
        else:
            bare_hole(teensy, num, x, ry)
outline(teensy, -30.5, -8.9, 30.5, 8.9)
teensy.SetPosition(P(TX, TY)); board.Add(teensy)
num_net = {}
for row, names, num0 in (("n", T_NEAR, 1), ("f", T_FAR, 48)):
    for i, nm in enumerate(names):
        n = T_USED.get((row, nm))
        if n:
            num_net[str(num0 + i if row == "n" else num0 - i)] = n
for p in teensy.Pads():
    if p.GetNumber() in num_net:
        p.SetNet(net(num_net[p.GetNumber()]))
register(teensy)

# ---------------------------------------------------------------- MCP4728 breakout socket (Adafruit 4470), shifted +0.14 mm onto the grid
DX = 72.0 + (OX + 123 * G - 78.35); DY = 2.0
D1 = [("VCC", None), ("GND", "GND"), ("SCL", "SCL"), ("SDA", "SDA"), ("LDAC", None), ("RDY", None)]
D2 = [("GND", None), ("VA", "SP_A"), ("VB", "SP_B"), ("VC", "SP_C"), ("VD", "SP_D"), ("VCC", "+3V3")]
dac = pcbnew.FOOTPRINT(board); dac.SetReference("U2"); dac.SetValue("MCP4728 (socket)")
dac.SetFPID(pcbnew.LIB_ID("bumpem-carrier-milled", "MCP4728_Socket_SingleSided"))
D_PIN = {}
for row, items, ry, num0 in ((1, D1, 2.54, 1), (2, D2, 15.24, 7)):
    for i, (nm, n) in enumerate(items):
        x = 6.35 + 2.54 * i
        if n:
            pad = copper_pad(dac, num0 + i, x, ry, PAD_SOCKET, n); pad.SetNet(net(n)); D_PIN[(row, nm)] = (DX + x, DY + ry)
        else:
            bare_hole(dac, num0 + i, x, ry)
outline(dac, 0, 0, 25.4, 17.78)
dac.SetPosition(P(DX, DY)); board.Add(dac)
register(dac)

# ---------------------------------------------------------------- module plugs (Phoenix MSTB 2,5/5-GF-5,08), pads on B.Cu only
MODS = "ABCD"
TB_Y, TB_X0, TB_PITCH = H - 10.6, 9.5, 37.5
PLUG = {}
for k, m in enumerate(MODS):
    base = TB_X0 + TB_PITCH * k
    fp = pcbnew.FootprintLoad(KFP + "Connector_Phoenix_MSTB.pretty", "PhoenixContact_MSTB_2,5_5-GF-5,08_1x05_P5.08mm_Horizontal_ThreadedFlange")
    fp.SetReference(f"J{k + 1}"); fp.SetValue(f"Module {m}"); fp.SetPosition(P(base, TB_Y)); board.Add(fp)
    nets = {"1": f"EN_{m}", "2": f"SP_{m}", "3": "GND", "4": "GND", "5": f"FIN_{m}"}
    for p in fp.Pads():
        p.SetNet(net(nets[p.GetNumber()])); bottom_only(p)
    register(fp)
    PLUG[m] = base
    BODIES.append((base - 8.1, TB_Y - 2.5, base + 28.4, TB_Y + 10.5))

# ---------------------------------------------------------------- per module: 1 kOhm series (Teensy side F_x -> plug side FIN_x), 1 MOhm FIN_x -> EN_x
# The 1 kOhm resistors double as jumpers (their bodies bridge the tracks between their pads). The 1 MOhm pulls the force input
# to the module's enable line: armed (EN high), a loose force cable reads ~200 N -> over-force FAULT, as D23; disarmed it reads 0.
R1K = {"A": (59.5, 30.5, 270, "10.16"), "B": (67.32, 30.3, 270, "15.24"),    # pad 1 (F side), rotation (270: pad 2 below), pitch
       "C": (104.82, 28.2, 270, "10.16"), "D": (122.0, 26.0, 0, "10.16")}       # D: horizontal, pad 2 to the right
PU_Y = 78.0
for k, m in enumerate(MODS):
    x1k, y1k, rot1k, pitch = R1K[m]
    for ref, val, lib, (x, y, rot), nets in (
            (f"R{k + 1}", "1k", f"R_Axial_DIN0207_L6.3mm_D2.5mm_P{pitch}mm_Horizontal", (x1k, y1k, rot1k), (f"F_{m}", f"FIN_{m}")),
            (f"R{k + 5}", "1M", "R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", (PLUG[m], PU_Y, 0), (f"EN_{m}", f"FIN_{m}"))):
        fp = pcbnew.FootprintLoad(KFP + "Resistor_THT.pretty", lib)
        fp.SetReference(ref); fp.SetValue(val); fp.SetPosition(P(x, y)); fp.SetOrientationDegrees(rot); board.Add(fp)
        for p in fp.Pads():
            p.SetNet(net(nets[0] if p.GetNumber() == "1" else nets[1])); p.SetSize(P(PAD_R, PAD_R)); bottom_only(p)
        register(fp)
        bb = fp.GetBoundingBox(False, False)
        BODIES.append((pcbnew.ToMM(bb.GetX()), pcbnew.ToMM(bb.GetY()), pcbnew.ToMM(bb.GetRight()), pcbnew.ToMM(bb.GetBottom())))

# ---------------------------------------------------------------- mounting holes (unchanged: the carrier plate's standoffs)
for i, (x, y) in enumerate([(4.0, 32.0), (4.0, 58.0), (W - 4.0, 10.0), (W - 4.0, 45.0)]):
    fp = pcbnew.FootprintLoad(KFP + "MountingHole.pretty", "MountingHole_3.2mm_M3")
    fp.SetReference(f"H{i + 1}"); fp.SetValue("M3"); fp.SetPosition(P(x, y)); board.Add(fp)
    HOLES.append((x, y, 1.6))

# ================================================================ router: one copper layer, 8 directions, wire links as a last resort
NX, NY = int((W - OX) / G) + 1, int((H - OY) / G) + 1
def cx(i): return OX + i * G
def cy(j): return OY + j * G
def cell(x, y): return (int(round((x - OX) / G)), int(round((y - OY) / G)))
def idx(c): return c[1] * NX + c[0]

def seg_dist(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / L))
    return math.hypot(px - x1 - t * dx, py - y1 - t * dy)

def cells_near(x1, y1, x2, y2, d):
    d += 0.05
    i0, j0 = cell(min(x1, x2) - d, min(y1, y2) - d); i1, j1 = cell(max(x1, x2) + d, max(y1, y2) + d)
    out = []
    for i in range(max(0, i0 - 1), min(NX, i1 + 2)):
        for j in range(max(0, j0 - 1), min(NY, j1 + 2)):
            if seg_dist(cx(i), cy(j), x1, y1, x2, y2) < d:
                out.append(j * NX + i)
    return out

PADX = PAD_LINK / 2 - TW / 2 + 0.2          # extra room a wire-link pad needs compared with a track centre
BASE_T, BASE_P = bytearray(NX * NY), bytearray(NX * NY)
for j in range(NY):
    for i in range(NX):
        e = CL_EDGE + TW / 2
        if cx(i) < e or cx(i) > W - e or cy(j) < e or cy(j) > H - e:
            BASE_T[j * NX + i] = 1
        e += PADX
        if cx(i) < e or cx(i) > W - e or cy(j) < e or cy(j) > H - e:
            BASE_P[j * NX + i] = 1
for (x, y, r) in HOLES:
    for k in cells_near(x, y, x, y, r + CL_HOLE + TW / 2): BASE_T[k] = 1
    for k in cells_near(x, y, x, y, r + CL_HOLE + TW / 2 + PADX): BASE_P[k] = 1
PAD_CELLS = [(cells_near(x1, y1, x2, y2, r + CL_USED + TW / 2), cells_near(x1, y1, x2, y2, r + CL_USED + TW / 2 + PADX), n)
             for (x1, y1, x2, y2, r, n) in PADS]
STATIC = {}
def static(netname):
    if netname not in STATIC:
        bt, bp = bytearray(BASE_T), bytearray(BASE_P)
        for (ct, cp, n) in PAD_CELLS:
            if n != netname:
                for k in ct: bt[k] = 1
                for k in cp: bp[k] = 1
        STATIC[netname] = (bt, bp)
    return STATIC[netname]

TRACKS, LINKS = [], []      # (x1, y1, x2, y2, width, net) ; (x1, y1, x2, y2, net)
OCC_T, OCC_P, NETCELLS = {}, {}, {}

def occupy(x1, y1, x2, y2, half, netname):
    for k in cells_near(x1, y1, x2, y2, half + CL + TW / 2): OCC_T.setdefault(k, set()).add(netname)
    for k in cells_near(x1, y1, x2, y2, half + CL + TW / 2 + PADX): OCC_P.setdefault(k, set()).add(netname)

def add_track(x1, y1, x2, y2, w, netname):
    TRACKS.append((x1, y1, x2, y2, w, netname)); occupy(x1, y1, x2, y2, w / 2, netname)
    L = max(1, int(math.hypot(x2 - x1, y2 - y1) / (G / 2)))
    nc_ = NETCELLS.setdefault(netname, set())
    for t in range(L + 1):
        nc_.add(idx(cell(x1 + (x2 - x1) * t / L, y1 + (y2 - y1) * t / L)))

def add_link(x1, y1, x2, y2, netname):
    LINKS.append((x1, y1, x2, y2, netname))
    for (x, y) in ((x1, y1), (x2, y2)):
        for k in cells_near(x, y, x, y, PAD_LINK / 2 + CL_USED + TW / 2): OCC_T.setdefault(k, set()).add(netname)
        for k in cells_near(x, y, x, y, PAD_LINK / 2 + CL_USED + TW / 2 + PADX): OCC_P.setdefault(k, set()).add(netname)

def body_hit(x1, y1, x2, y2, netname):
    """A wire link lies on the top side: not across a part body, not over another net's pin or a bare socket hole."""
    for (a, b, c, d) in BODIES:
        if max(x1, x2) > a and min(x1, x2) < c and max(y1, y2) > b and min(y1, y2) < d:
            return True
    for (px1, py1, px2, py2, r, n) in PADS:
        if n != netname and seg_dist((px1 + px2) / 2, (py1 + py2) / 2, x1, y1, x2, y2) < r + 0.6:
            return True
    for (hx, hy, r) in HOLES:
        if seg_dist(hx, hy, x1, y1, x2, y2) < r + 0.6:
            return True
    return False

DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]
LINK_LENS = list(range(6, 42, 2))       # in cells: 3.8 .. 25.4 mm
LINK_COST = 40.0

def astar(netname, start, goals, allow_links):
    bt, bp = static(netname)
    def blk(k):
        if bt[k]: return True
        o = OCC_T.get(k); return bool(o) and (len(o) > 1 or netname not in o)
    def pblk(k):
        if bp[k]: return True
        o = OCC_P.get(k); return bool(o) and (len(o) > 1 or netname not in o)
    gl = [(k % NX, k // NX) for k in goals]
    sample = gl if len(gl) <= 60 else random.Random(0).sample(gl, 60)
    def h(i, j):
        return min(math.hypot(i - a, j - b) for (a, b) in sample) * G * 0.9
    s = idx(start)
    best, came, ddir, cnt = {s: 0.0}, {}, {s: -1}, 0
    openq = [(h(*start), 0, 0.0, s)]
    while openq:
        f, _, g, k = heapq.heappop(openq)
        if g > best.get(k, 1e18) + 1e-9:
            continue
        if k in goals:
            path = [(k, None)]
            while k in came:
                k, kind = came[k]; path.append((k, kind))
            return list(reversed(path))
        i, j, d = k % NX, k // NX, ddir[k]
        for n_, (di, dj) in enumerate(DIRS):
            ni, nj = i + di, j + dj
            if not (0 <= ni < NX and 0 <= nj < NY):
                continue
            nk = nj * NX + ni
            if blk(nk) and nk not in goals:
                continue
            if di and dj and (blk(j * NX + ni) or blk(nj * NX + i)) and nk not in goals:
                continue
            ng = g + G * (1.4142 if di and dj else 1.0) + (0.0 if d in (-1, n_) else 0.4)
            if ng < best.get(nk, 1e18) - 1e-9:
                best[nk] = ng; came[nk] = (k, "t"); ddir[nk] = n_; cnt += 1
                heapq.heappush(openq, (ng + h(ni, nj), cnt, ng, nk))
        if allow_links and not pblk(k):
            for (di, dj) in DIRS[:4]:
                for L in LINK_LENS:
                    ni, nj = i + di * L, j + dj * L
                    if not (0 <= ni < NX and 0 <= nj < NY):
                        break
                    nk = nj * NX + ni
                    if pblk(nk):
                        continue
                    ng = g + LINK_COST + L * G
                    if ng < best.get(nk, 1e18) - 1e-9 and not body_hit(cx(i), cy(j), cx(ni), cy(nj), netname):
                        best[nk] = ng; came[nk] = (k, "link"); ddir[nk] = -1; cnt += 1
                        heapq.heappush(openq, (ng + h(ni, nj), cnt, ng, nk))
    return None

def commit(netname, path, width, start_xy, end_xy):
    """path: [(cell index, kind of move into the next)]; 'link' = wire link from this cell to the next."""
    runs, pts = [], []
    for n_, (k, kind) in enumerate(path):
        pts.append((cx(k % NX), cy(k // NX)))
        if kind == "link":
            runs.append(pts); nk = path[n_ + 1][0]
            add_link(cx(k % NX), cy(k // NX), cx(nk % NX), cy(nk // NX), netname); pts = []
    runs.append(pts)
    if start_xy: runs[0] = [start_xy] + runs[0]
    if end_xy: runs[-1] = runs[-1] + [end_xy]
    for pts in runs:
        simp = [pts[0]]
        for n_ in range(1, len(pts) - 1):
            (x0, y0), (x1, y1), (x2, y2) = simp[-1], pts[n_], pts[n_ + 1]
            if abs((x1 - x0) * (y2 - y1) - (y1 - y0) * (x2 - x1)) > 1e-6:
                simp.append(pts[n_])
        if len(pts) > 1:
            simp.append(pts[-1])
        for (x1, y1), (x2, y2) in zip(simp, simp[1:]):
            if math.hypot(x2 - x1, y2 - y1) > 1e-6:
                add_track(x1, y1, x2, y2, width, netname)

def pad_xy(netname):
    return [((x1 + x2) / 2, (y1 + y2) / 2) for (x1, y1, x2, y2, r, n) in PADS if n == netname]

def route_net(netname, width, allow_links=True):
    terms = pad_xy(netname)
    if len(terms) < 2:
        return True
    done = [terms[0]]
    rest = sorted(terms[1:], key=lambda t: math.hypot(t[0] - terms[0][0], t[1] - terms[0][1]))
    for t in rest:
        goals = {idx(cell(*d)) for d in done} | NETCELLS.get(netname, set())
        path = astar(netname, cell(*t), goals, allow_links)
        if path is None:
            print("  no path:", netname, t, flush=True)
            return False
        end = path[-1][0]
        end_xy = next((d for d in done if idx(cell(*d)) == end), None)
        commit(netname, path, width, t, end_xy)
        done.append(t)
    return True

# ---------------------------------------------------------------- fixed routes (hand-planned topology, see milled/README.md)
FIXED, FIXED_LINKS = [], []
def ftrack(netname, pts, w=TW):
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        FIXED.append((x1, y1, x2, y2, w, netname))
# ground: left edge, bus under the plugs, right edge, top edge to the DAC's GND (row 1)
gx1, gx2, gy_bus, gy_top = 1.4, W - 1.4, 91.0, 1.4
t1 = T_PIN[("n", "GND")]
ftrack("GND", [t1, (gx1, t1[1] + (t1[0] - gx1)), (gx1, gy_bus - 1.0), (gx1 + 1.0, gy_bus), (gx2 - 1.0, gy_bus), (gx2, gy_bus - 1.0),
               (gx2, gy_top + 1.0), (gx2 - 1.0, gy_top)], GW)
dg = D_PIN[(1, "GND")]
ftrack("GND", [(gx2 - 1.0, gy_top), (dg[0] + 1.0, gy_top), (dg[0], gy_top + 1.0), dg], GW)
for m in MODS:
    for dx in (10.16, 15.24):
        ftrack("GND", [(PLUG[m] + dx, gy_bus), (PLUG[m] + dx, TB_Y)], GW)
# force lines: up over the Teensy's far row (F_D outermost), right, down between the Teensy and the DAC: they arrive A, B, C, D
F_LANE = {"A": (4.5, 62.4), "B": (3.35, 63.55), "C": (2.2, 64.7), "D": (1.05, 65.85)}
FW = 0.45                                                   # 4 lanes between the board edge and the far row
for m, pin in zip("ABCD", ["14", "15", "16", "17"]):
    (px, py), (ly, dx) = T_PIN[("f", pin)], F_LANE[m]
    ftrack(f"F_{m}", [(px, py), (px, ly), (dx, ly), (dx, 24.0)], FW)
# I2C and 3.3 V: under the Teensy (B_T), wire links over the four force lines, into the DAC from below; SCL/SDA links cross on top
sda, scl = T_PIN[("f", "18")], T_PIN[("f", "19")]
ftrack("SDA", [sda, (sda[0], 9.6), (59.6, 9.6)])
ftrack("SCL", [scl, (scl[0], 12.6), (59.6, 12.6)])
FIXED_LINKS += [(59.6, 9.6, 68.5, 12.6, "SDA"), (59.6, 12.6, 68.5, 9.6, "SCL"), (59.6, 15.6, 68.5, 15.6, "+3V3")]
dscl, dsda, dvcc = D_PIN[(1, "SCL")], D_PIN[(1, "SDA")], D_PIN[(2, "VCC")]
ftrack("SCL", [(68.5, 9.6), (dscl[0], 9.6), dscl])
ftrack("SDA", [(68.5, 12.6), (dsda[0], 12.6), dsda])
v3 = T_PIN[("n", "3V3")]
ftrack("+3V3", [v3, (v3[0], 15.6), (59.6, 15.6)], PW)
ftrack("+3V3", [(68.5, 15.6), (69.2, 14.9), (dvcc[0], 14.9), dvcc], PW)

# ---------------------------------------------------------------- below the Teensy and the DAC: lanes (y) and jumps, see milled/README.md
# lane order top -> bottom: SP_D 22.0, EN_A 25.6, F_D 26.0, F_C 28.2, F_B 30.3, EN_D 33.6, EN_C 35.2, SP_A 37.4, FIN_A 40.66, SP_B 42.8
# jumps: R1 (F_A) over EN_D EN_C SP_A; R2 (F_B) over EN_D EN_C SP_A SP_B; R3 (F_C) over EN_D; R4 (F_D) over SP_D;
#        links: SP_A, SP_B over F_D F_C EN_D EN_C; SP_C over F_D F_C EN_D; EN_B over SP_A FIN_A. Pull-ups R5-R8 bridge SP_x.
def plug(m, i):
    return (PLUG[m] + 5.08 * i, TB_Y)
en = {m: T_PIN[("n", p)] for m, p in zip(MODS, ["27", "28", "29", "30"])}
sp = {m: D_PIN[(2, v)] for m, v in zip(MODS, ["VA", "VB", "VC", "VD"])}
PU = {m: ((PLUG[m], PU_Y), (PLUG[m] + 10.16, PU_Y)) for m in MODS}          # pull-up pad 1 (EN), pad 2 (FIN)
R1P = {m: ((R1K[m][0], R1K[m][1]), (R1K[m][0] + (float(R1K[m][3]) if R1K[m][2] == 0 else 0), R1K[m][1] + (float(R1K[m][3]) if R1K[m][2] == 270 else 0)))
       for m in MODS}                                                       # 1k pad 1 (F), pad 2 (FIN)
# enables
ftrack("EN_A", [en["A"], (en["A"][0], 25.6), (PLUG["A"], 25.6), PU["A"][0], plug("A", 0)])
ftrack("EN_B", [en["B"], (en["B"][0], 23.4), (49.5, 24.45), (49.5, 34.0)])
FIXED_LINKS.append((49.5, 34.0, 49.5, 44.0, "EN_B"))
ftrack("EN_B", [(49.5, 44.0), (PLUG["B"], 46.5), PU["B"][0], plug("B", 0)])
ftrack("EN_C", [en["C"], (en["C"][0], 35.2), (PLUG["C"], 35.2), PU["C"][0], plug("C", 0)])
ftrack("EN_D", [en["D"], (en["D"][0], 33.6), (PLUG["D"], 33.6), PU["D"][0], plug("D", 0)])
# setpoints
ftrack("SP_A", [sp["A"], (79.0, 19.27), (79.0, 20.4)])
FIXED_LINKS.append((79.0, 20.4, 79.0, 37.4, "SP_A"))
ftrack("SP_A", [(79.0, 37.4), (plug("A", 1)[0], 37.4), plug("A", 1)])
ftrack("SP_B", [sp["B"], (sp["B"][0], 19.0), (82.3, 20.27), (82.3, 20.4)])
FIXED_LINKS.append((82.3, 20.4, 82.3, 42.8, "SP_B"))
ftrack("SP_B", [(82.3, 42.8), (plug("B", 1)[0], 42.8), plug("B", 1)])
ftrack("SP_C", [sp["C"], (sp["C"][0], 20.4)])
FIXED_LINKS.append((sp["C"][0], 20.4, 86.8, 36.5, "SP_C"))
ftrack("SP_C", [(86.8, 36.5), (plug("C", 1)[0], 36.5 + (plug("C", 1)[0] - 86.8)), plug("C", 1)])
ftrack("SP_D", [sp["D"], (sp["D"][0], 22.0), (plug("D", 1)[0], 22.0), plug("D", 1)])
# force: Teensy side (F_x) to the 1k, plug side (FIN_x) to the plug and the pull-up
ftrack("F_A", [(F_LANE["A"][1], 24.0), (59.5, 26.9), R1P["A"][0]], FW)
ftrack("F_B", [(F_LANE["B"][1], 24.0), (F_LANE["B"][1], 30.3), R1P["B"][0]], FW)
ftrack("F_C", [(F_LANE["C"][1], 24.0), (F_LANE["C"][1], 28.2), R1P["C"][0]], FW)
ftrack("F_D", [(F_LANE["D"][1], 24.0), (F_LANE["D"][1], 26.0), R1P["D"][0]], FW)
ftrack("FIN_A", [R1P["A"][1], (plug("A", 4)[0], 40.66), (plug("A", 4)[0], PU_Y), plug("A", 4)])
ftrack("FIN_A", [(plug("A", 4)[0], PU_Y), PU["A"][1]])
for m in "BCD":
    ftrack(f"FIN_{m}", [R1P[m][1], (R1P[m][1][0], PU_Y)] + ([] if m == "D" else []))
ftrack("FIN_B", [(R1P["B"][1][0], PU_Y), plug("B", 4)]); ftrack("FIN_B", [(R1P["B"][1][0], PU_Y), PU["B"][1]])
ftrack("FIN_C", [(R1P["C"][1][0], PU_Y), plug("C", 4)]); ftrack("FIN_C", [(R1P["C"][1][0], PU_Y), PU["C"][1]])
ftrack("FIN_D", [(R1P["D"][1][0], PU_Y), (plug("D", 4)[0], PU_Y), plug("D", 4)])

FIRST, MIDDLE, LAST = [], [], []
WIDTH = {"+3V3": PW}

def dump(path=os.environ.get("DUMP")):
    if path:
        import json
        json.dump(dict(pads=PADS, holes=HOLES, tracks=TRACKS, links=LINKS, bodies=BODIES), open(path, "w"))

def attempt(order):
    del TRACKS[:]; del LINKS[:]; OCC_T.clear(); OCC_P.clear(); NETCELLS.clear()
    for t in FIXED:
        add_track(*t)
    for l in FIXED_LINKS:
        add_link(*l)
    for n in order:
        if not route_net(n, WIDTH.get(n, TW)):
            dump(); return None
    return (len(LINKS), sum(math.hypot(x2 - x1, y2 - y1) for (x1, y1, x2, y2, w, n) in TRACKS))

if __name__ == "__main__":
    tries = int(os.environ.get("TRIES", "1"))
    rnd = random.Random(int(os.environ.get("SEED", "1")))
    best = None
    for t in range(tries):
        order = FIRST + (rnd.sample(MIDDLE, len(MIDDLE)) if t else MIDDLE) + LAST
        res = attempt(order)
        print(f"try {t}: {'failed' if res is None else f'{res[0]} links, {res[1]:.0f} mm'}", flush=True)
        if res and (best is None or res < best[0]):
            best = (res, order)
    if best is None:
        sys.exit("no routing found")
    attempt(best[1]); dump()
    print("best order:", best[1], "links:", len(LINKS))
    for (x1, y1, x2, y2, w, n) in TRACKS:
        t = pcbnew.PCB_TRACK(board); t.SetStart(P(x1, y1)); t.SetEnd(P(x2, y2)); t.SetWidth(mm(w))
        t.SetLayer(pcbnew.B_Cu); t.SetNet(net(n)); board.Add(t)
    for k, (x1, y1, x2, y2, n) in enumerate(LINKS):
        fp = pcbnew.FOOTPRINT(board); fp.SetReference(f"W{k + 1}"); fp.SetValue("wire link")
        fp.SetFPID(pcbnew.LIB_ID("bumpem-carrier-milled", "Wire_Link"))
        fp.Reference().SetLayer(pcbnew.F_Fab); fp.Value().SetLayer(pcbnew.F_Fab); fp.Value().SetVisible(False)
        for num, (x, y) in ((1, (0.0, 0.0)), (2, (x2 - x1, y2 - y1))):
            pad = pcbnew.PAD(fp); pad.SetAttribute(pcbnew.PAD_ATTRIB_PTH); pad.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
            pad.SetSize(P(PAD_LINK, PAD_LINK)); pad.SetDrillSize(P(0.9, 0.9)); pad.SetNumber(str(num)); bottom_only(pad)
            pad.SetFPRelativePosition(P(x, y)); fp.Add(pad)
        s = pcbnew.PCB_SHAPE(fp); s.SetShape(pcbnew.SHAPE_T_SEGMENT); s.SetStart(P(0, 0)); s.SetEnd(P(x2 - x1, y2 - y1))
        s.SetLayer(pcbnew.F_Fab); s.SetWidth(mm(0.6)); fp.Add(s)
        fp.AddNetTiePadGroup("1, 2")                                # the wire joins its two pads
        fp.SetPosition(P(x1, y1)); board.Add(fp)
        fp.Reference().SetPosition(P((x1 + x2) / 2 + 1.0, (y1 + y2) / 2))
        for pad in fp.Pads():
            pad.SetNet(net(n))
    def ctext(txt, x, y, size=1.5):                                 # copper text on the bottom, readable from below
        t = pcbnew.PCB_TEXT(board); t.SetText(txt); t.SetPosition(P(x, y)); t.SetLayer(pcbnew.B_Cu)
        t.SetTextSize(P(size, size)); t.SetTextThickness(mm(0.3)); t.SetMirrored(True); board.Add(t)
    for m in MODS:
        ctext(m, PLUG[m] - 4.5, TB_Y + 0.2, 2.5)                      # module letter beside each plug's EN pin
    ctext("Bump'em v2", 38.5, 58.0, 1.2)
    ctext("solder side", 38.5, 61.0, 1.2)
    for a, b in (((0, 0), (W, 0)), ((W, 0), (W, H)), ((W, H), (0, H)), ((0, H), (0, 0))):
        s = pcbnew.PCB_SHAPE(board); s.SetShape(pcbnew.SHAPE_T_SEGMENT); s.SetStart(P(*a)); s.SetEnd(P(*b))
        s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(mm(0.1)); board.Add(s)
    board.Save(OUT)
    print("written", OUT)

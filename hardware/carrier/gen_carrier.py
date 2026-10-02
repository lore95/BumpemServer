"""Generate the Bump'em carrier board (Teensy 4.1 + MCP4728 + 4 module terminals) with KiCad's pcbnew API.

Run with KiCad's Python (8.x):
  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3 gen_carrier.py
Writes bumpem-carrier.kicad_pcb and bumpem-carrier.pretty/ next to this file.

Sources: docs/knowledge/wiring.md, docs/diagrams/cabling-4-modules.png (pins), firmware/src/main.ino (pin numbers),
Teensy 4.1 pin order: XenGi/teensy_library (MIT), Adafruit MCP4728 (product 4470) pad layout: adafruit/Adafruit-MCP4728-PCB.
Coordinates in mm, origin top-left, y down. Copper: B.Cu mostly vertical, F.Cu mostly horizontal (Manhattan).
"""
import math
import os
import sys
import pcbnew
import wx

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import netlist as NL

_app = wx.App(False)   # the zone filler needs a wx application object

HERE = os.path.dirname(os.path.abspath(__file__))
KFP = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/"
PREVIEW = os.environ.get("PREVIEW")   # path: write a copy without pours/stitching (for review renders)
OUT = PREVIEW or os.path.join(HERE, "bumpem-carrier.kicad_pcb")
LIB = os.path.join(HERE, "bumpem-carrier.pretty")

W, H = 120.0, 93.5          # board size
TRACK, POWER = 0.5, 0.8     # track widths
CLEAR = 0.3                 # copper clearance
VIA_D, VIA_DRILL = 1.4, 0.8

mm = pcbnew.FromMM
def P(x, y):
    return pcbnew.VECTOR2I(mm(x), mm(y))

board = pcbnew.BOARD()
ds = board.GetDesignSettings()
nc = ds.m_NetSettings.m_DefaultNetClass
nc.SetClearance(mm(CLEAR)); nc.SetTrackWidth(mm(TRACK)); nc.SetViaDiameter(mm(VIA_D)); nc.SetViaDrill(mm(VIA_DRILL))
ds.m_MinClearance = mm(CLEAR); ds.m_TrackMinWidth = mm(0.3); ds.m_ViasMinSize = mm(1.0); ds.m_MinThroughDrill = mm(0.6)
ds.m_CopperEdgeClearance = mm(0.5)

NETS = {}
def net(name):
    if name not in NETS:
        n = pcbnew.NETINFO_ITEM(board, name, len(NETS) + 1); board.Add(n); NETS[name] = n
    return NETS[name]

MODS = "ABCD"
ROLE = {"A": "left", "B": "front", "C": "right", "D": "back"}

# ---------------------------------------------------------------- geometry log (for stitching-via clearance)
SEGS, DOTS = [], []          # (x1,y1,x2,y2,halfwidth,layer) ; (x,y,radius,layers)

def track(netname, layer, pts, w=TRACK):
    lay = pcbnew.F_Cu if layer == "F" else pcbnew.B_Cu
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(P(x1, y1)); t.SetEnd(P(x2, y2)); t.SetWidth(mm(w)); t.SetLayer(lay); t.SetNet(net(netname))
        board.Add(t)
        SEGS.append((x1, y1, x2, y2, w / 2, layer))

def via(netname, x, y):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(P(x, y)); v.SetWidth(mm(VIA_D)); v.SetDrill(mm(VIA_DRILL)); v.SetNet(net(netname))
    v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    board.Add(v)
    DOTS.append((x, y, VIA_D / 2, "FB"))

def text(s, x, y, size=1.0, layer=pcbnew.F_SilkS, bold=False, just=0):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(s); t.SetPosition(P(x, y)); t.SetLayer(layer)
    t.SetTextSize(P(size, size)); t.SetTextThickness(mm(size * (0.2 if bold else 0.15)))
    if just:
        t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT if just < 0 else pcbnew.GR_TEXT_H_ALIGN_RIGHT)
    if layer == pcbnew.B_SilkS:
        t.SetMirrored(True)
    board.Add(t)

def line(x1, y1, x2, y2, layer=pcbnew.F_SilkS, w=0.15):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT); s.SetStart(P(x1, y1)); s.SetEnd(P(x2, y2)); s.SetLayer(layer); s.SetWidth(mm(w))
    board.Add(s)

def rect(x1, y1, x2, y2, layer, w=0.15, fp=None):
    for a, b in (((x1, y1), (x2, y1)), ((x2, y1), (x2, y2)), ((x2, y2), (x1, y2)), ((x1, y2), (x1, y1))):
        s = pcbnew.PCB_SHAPE(fp or board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT); s.SetStart(P(*a)); s.SetEnd(P(*b)); s.SetLayer(layer); s.SetWidth(mm(w))
        (fp or board).Add(s)

def place(lib, name, ref, value, x, y, rot=0, nets=None):
    fp = pcbnew.FootprintLoad(KFP + lib + ".pretty", name)
    fp.SetFPID(pcbnew.LIB_ID(lib, name)); fp.SetPath(pcbnew.KIID_PATH("/" + NL.sym_uuid(ref)))
    fp.SetReference(ref); fp.SetValue(value)
    fp.SetPosition(P(x, y)); fp.SetOrientationDegrees(rot)
    board.Add(fp)
    for pad in fp.Pads():
        n = (nets or {}).get(pad.GetNumber())
        if n:
            pad.SetNet(net(n))
        c = pad.GetPosition()
        DOTS.append((pcbnew.ToMM(c.x), pcbnew.ToMM(c.y), pcbnew.ToMM(max(pad.GetSize().x, pad.GetSize().y)) / 2, "FB"))
    return fp

# ---------------------------------------------------------------- custom footprints: Teensy 4.1 socket, MCP4728 breakout socket
def socket_fp(name, rows, pitch=2.54, outline=None, ref="U", value=""):
    """rows: list of (x, y, number, kind, netname); kind 'pth' | 'mech' (full pad, unused) | 'small' (1.3 mm pad, unused)."""
    fp = pcbnew.FOOTPRINT(board)
    fp.SetFPID(pcbnew.LIB_ID("bumpem-carrier", name))
    fp.SetReference(ref); fp.SetValue(value); fp.SetPath(pcbnew.KIID_PATH("/" + NL.sym_uuid(ref)))
    for x, y, num, kind, _ in rows:
        pad = pcbnew.PAD(fp)
        if kind == "small":     # unused pin: small plated pad so traces fit between neighbours
            pad.SetAttribute(pcbnew.PAD_ATTRIB_PTH); pad.SetLayerSet(pad.PTHMask())
            pad.SetSize(P(1.3, 1.3)); pad.SetDrillSize(P(1.0, 1.0)); pad.SetNumber(str(num))
        else:
            pad.SetAttribute(pcbnew.PAD_ATTRIB_PTH); pad.SetLayerSet(pad.PTHMask())
            pad.SetSize(P(1.8, 1.8)); pad.SetDrillSize(P(1.0, 1.0)); pad.SetNumber(str(num))
        pad.SetShape(pcbnew.PAD_SHAPE_RECT if str(num) == "1" else pcbnew.PAD_SHAPE_CIRCLE)
        pad.SetFPRelativePosition(P(x, y))
        fp.Add(pad)
    if outline:
        x1, y1, x2, y2 = outline
        rect(x1, y1, x2, y2, pcbnew.F_SilkS, 0.15, fp)
        rect(x1 - 0.25, y1 - 0.25, x2 + 0.25, y2 + 0.25, pcbnew.F_CrtYd, 0.05, fp)
    return fp

# Teensy 4.1, USB to the left. Pin names per pad (XenGi/teensy_library, Teensy4.1 symbol)
T_BOTTOM = ["GND"] + [str(i) for i in range(13)] + ["3V3"] + [str(i) for i in range(24, 33)]          # pads 1..24, left -> right
T_TOP = ["VIN", "GND", "3V3"] + [str(i) for i in range(23, 12, -1)] + ["GND"] + [str(i) for i in range(41, 32, -1)]  # pads 48..25, left -> right
T_NET = {("b", "GND"): "GND", ("b", "3V3"): "+3V3", ("b", "27"): "EN_A", ("b", "28"): "EN_B", ("b", "29"): "EN_C", ("b", "30"): "EN_D",
         ("t", "19"): "SCL", ("t", "18"): "SDA", ("t", "17"): "F_D", ("t", "16"): "F_C", ("t", "15"): "F_B", ("t", "14"): "F_A",
         ("t", "GND"): "GND"}
T_MECH = {("t", "VIN"), ("t", "3V3"), ("t", "33"), ("b", "32")}     # soldered for strength, not connected (VIN = 5 V: never connect)
TX, TY = 31.5, 14.0                                                 # Teensy centre
t_rows, t_pin = [], {}
for i, name in enumerate(T_BOTTOM):
    x, y, num = -29.21 + 2.54 * i, 7.62, i + 1
    n = T_NET.get(("b", name)); kind = "pth" if n else ("mech" if ("b", name) in T_MECH else "small")
    t_rows.append((x, y, num, kind, n)); t_pin[("b", name)] = (TX + x, TY + y)
for i, name in enumerate(T_TOP):
    x, y, num = -29.21 + 2.54 * i, -7.62, 48 - i
    n = T_NET.get(("t", name)); kind = "pth" if n else ("mech" if ("t", name) in T_MECH else "small")
    t_rows.append((x, y, num, kind, n)); t_pin.setdefault(("t", name), (TX + x, TY + y))
teensy = socket_fp("Teensy41_Socket", t_rows, outline=(-30.5, -8.9, 30.5, 8.9), ref="U1", value="Teensy 4.1")
teensy.SetPosition(P(TX, TY)); board.Add(teensy)
def assign(fp, rows, names):
    """Nets by pad position; unused PTH pads get KiCad's 'unconnected-(ref-pin-PadN)' net, as Update-PCB-from-schematic would."""
    by_pos = {(round(x, 2), round(y, 2)): (kind, n, num) for x, y, num, kind, n in rows}
    for pad in fp.Pads():
        rel = pad.GetFPRelativePosition()
        kind, n, num = by_pos[(round(pcbnew.ToMM(rel.x), 2), round(pcbnew.ToMM(rel.y), 2))]
        if n:
            pad.SetNet(net(n))
        else:
            pad.SetNet(net(f"unconnected-({fp.GetReference()}-{names[str(num)]}-Pad{num})"))
        c = pad.GetPosition(); DOTS.append((pcbnew.ToMM(c.x), pcbnew.ToMM(c.y), 0.9 if kind != "small" else 0.65, "FB"))
assign(teensy, t_rows, NL.TEENSY_PINS)
text("USB", 3.2, 14.0, 1.2)
text("Teensy 4.1 · socket · USB this end", 31.5, 17.6, 1.2)
text("5V: NOT connected", 2.0, 4.4, 0.9, just=-1)

# Adafruit MCP4728 (4470): JP1 VCC GND SCL SDA LDAC RDY, JP2 GND VA VB VC VD VCC (12.7 mm apart)
DX, DY = 72.0, 2.0                                                 # breakout top-left corner
D_JP1 = [("VCC", None), ("GND", "GND"), ("SCL", "SCL"), ("SDA", "SDA"), ("LDAC", None), ("RDY", None)]
D_JP2 = [("GND", "GND"), ("VA", "SP_A"), ("VB", "SP_B"), ("VC", "SP_C"), ("VD", "SP_D"), ("VCC", "+3V3")]
d_rows, d_pin = [], {}
for i, (nm, n) in enumerate(D_JP1):
    d_rows.append((6.35 + 2.54 * i, 2.54, i + 1, "pth" if n else "mech", n)); d_pin[("1", nm)] = (DX + 6.35 + 2.54 * i, DY + 2.54)
for i, (nm, n) in enumerate(D_JP2):
    d_rows.append((6.35 + 2.54 * i, 15.24, 7 + i, "pth" if n else "mech", n)); d_pin[("2", nm)] = (DX + 6.35 + 2.54 * i, DY + 15.24)
dac = socket_fp("Adafruit_MCP4728_Socket", d_rows, outline=(0, 0, 25.4, 17.78), ref="U2", value="MCP4728 (Adafruit 4470)")
dac.SetPosition(P(DX, DY)); board.Add(dac)
dac.Reference().SetPosition(P(DX + 22.5, DY + 8.9))
assign(dac, d_rows, NL.DAC_PINS)
for i, (nm, _) in enumerate(D_JP1):
    text(nm, DX + 6.35 + 2.54 * i, DY + (5.0 if i % 2 == 0 else 6.3), 0.8)
for i, (nm, _) in enumerate(D_JP2):
    text(nm, DX + 6.35 + 2.54 * i, DY + 12.6, 0.8)
text("MCP4728", DX + 12.7, DY + 8.9, 1.2)

# ---------------------------------------------------------------- terminal blocks: one 5-way block per module, wires enter at the bottom edge
TB_Y = 88.0
TB_X0, TB_PITCH = 10.0, 26.67
PIN = ["EN", "SP+", "SP-", "GND", "F"]           # pad 1..5, same order as docs/diagrams/cabling-4-modules.png
COLOUR = ["yel", "blu", "grn", "wht", "brn"]
tb = {}
for k, m in enumerate(MODS):
    base = TB_X0 + TB_PITCH * k                      # x of pad 5 (F); rotated 180 deg so pad 1 (EN) is rightmost
    nets = {"1": f"EN_{m}", "2": f"SP_{m}", "3": "GND", "4": "GND", "5": f"FIN_{m}"}
    j = place("TerminalBlock_Phoenix", "TerminalBlock_Phoenix_MKDS-1,5-5-5.08_1x05_P5.08mm_Horizontal",
              f"J{k + 1}", f"Module {m}", base + 20.32, TB_Y, 180, nets)
    j.Reference().SetVisible(False)
    for i in range(5):
        x = base + 20.32 - 5.08 * i
        tb[(m, PIN[i])] = (x, TB_Y)
        text(PIN[i], x + (1.6 if PIN[i] == "F" else 0), 80.9, 0.8, bold=True)
        text(COLOUR[i], x, 82.3, 0.8)
    text(f"{m} · {ROLE[m]}" if ROLE[m] else m, base + 12.5, 75.0, 1.1, bold=True)

# ---------------------------------------------------------------- force-input protection, one column above each F terminal
# FIN (terminal) -> R_series -> F_x node -> Teensy pin; node -> R_pulldown -> GND; node -> Schottky -> +3V3
NODE_Y, FT_Y, PD_Y, K_Y = 69.84, 80.0, 77.46, 62.22
for k, m in enumerate(MODS):
    fx = tb[(m, "F")][0]
    place("Resistor_THT", "R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", f"R{k + 1}", "1k", fx, NODE_Y, 270,
          {"1": f"F_{m}", "2": f"FIN_{m}"})
    rp = place("Resistor_THT", "R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal", f"R{k + 5}", "1M", fx - 3.81, NODE_Y, 270,
               {"1": f"F_{m}", "2": "GND"})
    rp.Reference().SetPosition(P(fx - 6.3, NODE_Y + 3.81))
    place("Diode_THT", "D_DO-35_SOD27_P7.62mm_Horizontal", f"D{k + 1}", "BAT85", fx + 3.81, K_Y, 270,
          {"1": "+3V3", "2": f"F_{m}"})
    track(f"F_{m}", "B", [(fx - 3.81, NODE_Y), (fx + 3.81, NODE_Y)])
    track(f"FIN_{m}", "B", [(fx, FT_Y), tb[(m, "F")]])

# ---------------------------------------------------------------- routing
# bands (F.Cu horizontals), see hardware/carrier/README.md "Routing"
BAND = {"F_D": 30.0, "F_C": 32.5, "F_B": 35.0, "F_A": 37.5, "SP_A": 40.0, "SP_B": 42.5, "SP_C": 45.0, "SP_D": 47.5,
        "EN_A": 50.0, "EN_B": 52.5, "EN_C": 55.0, "EN_D": 57.5}

def manhattan(name, src, src_x, dst_x, dst_y, w=TRACK, jog=None, dst_via_x=None, dst_jog_dy=1.5):
    """src pad -> B.Cu down (optional jog) -> via -> F.Cu horizontal on its band -> via -> B.Cu down to (dst_x, dst_y).
    dst_via_x: put the second via beside dst_x and jog back on B.Cu (keeps it clear of a neighbouring track)."""
    y = BAND[name]
    vx = dst_x if dst_via_x is None else dst_via_x
    pts = [src] + (jog or []) + [(src_x, y)]
    track(name, "B", pts, w); via(name, src_x, y)
    track(name, "F", [(src_x, y), (vx, y)], w); via(name, vx, y)
    back = [] if vx == dst_x else [(vx, y + dst_jog_dy), (dst_x, y + dst_jog_dy + abs(vx - dst_x))]
    track(name, "B", [(vx, y)] + back + [(dst_x, dst_y)], w)

def jog_to(sx, y0, x):
    """leave a pad straight down to y0, then 45 degrees to column x"""
    return [(sx, y0), (x, y0 + abs(x - sx))] if abs(x - sx) > 1e-6 else []

# Teensy force inputs (top row): along the free space under the Teensy, out past its right end, then down.
# They pass no socket pin, so a solder blob on the socket cannot reach a force signal.
F_CH_Y = {"A": 9.5, "B": 11.0, "C": 12.5, "D": 14.0}     # under the Teensy
F_COL_X = {"D": 64.0, "C": 66.0, "B": 68.0, "A": 70.0}   # between the Teensy and the DAC
for m, pin in zip("DCBA", ["17", "16", "15", "14"]):
    sx, sy = t_pin[("t", pin)]
    manhattan(f"F_{m}", (sx, sy), F_COL_X[m], tb[(m, "F")][0], NODE_Y, jog=[(sx, F_CH_Y[m]), (F_COL_X[m], F_CH_Y[m])])
# enables (bottom row) down; B and C shifted sideways to keep >= 0.6 mm from the neighbouring vias
EN_COL_X = {"A": None, "B": 49.9, "C": 53.6, "D": None}
for m, pin in zip(MODS, ["27", "28", "29", "30"]):
    sx, sy = t_pin[("b", pin)]
    x = EN_COL_X[m] or sx
    manhattan(f"EN_{m}", (sx, sy), x, tb[(m, "EN")][0], TB_Y, jog=jog_to(sx, 23.6, x),
              dst_via_x=57.8 if m == "B" else None, dst_jog_dy=7.0)    # B rejoins its column below EN_D's via
# DAC outputs down; D shifted sideways to keep >= 0.6 mm from F_D's via
for m, nm in zip(MODS, ["VA", "VB", "VC", "VD"]):
    sx, sy = d_pin[("2", nm)]
    x = 88.0 if m == "D" else sx
    manhattan(f"SP_{m}", (sx, sy), x, tb[(m, "SP+")][0], TB_Y, jog=jog_to(sx, 19.0, x))

# I2C: Teensy 19 -> DAC SCL on F.Cu, Teensy 18 -> DAC SDA on B.Cu (they cross in plan, on different layers)
sx, sy = t_pin[("t", "19")]; dx, dy = d_pin[("1", "SCL")]
track("SCL", "F", [(sx, sy), (sx, 1.2), (dx, 1.2), (dx, dy)])
sx, sy = t_pin[("t", "18")]; dx, dy = d_pin[("1", "SDA")]
track("SDA", "B", [(sx, sy), (sx, 2.6), (dx, 2.6), (dx, dy)])

# +3V3: Teensy 3V3 (bottom row) -> bus on F.Cu under the clamp diodes; branch up to DAC VCC (JP2)
sx, sy = t_pin[("b", "3V3")]
track("+3V3", "B", [(sx, sy), (sx, 23.6), (39.0, 24.75), (39.0, K_Y)], POWER); via("+3V3", 39.0, K_Y)
kx = [tb[(m, "F")][0] + 3.81 for m in MODS]
track("+3V3", "F", [(kx[0], K_Y), (kx[-1] + 2.69, K_Y)], POWER); via("+3V3", kx[-1] + 2.69, K_Y)
vx, vy = d_pin[("2", "VCC")]
track("+3V3", "B", [(kx[-1] + 2.69, K_Y), (kx[-1] + 2.69, 20.2), (vx, 20.2), (vx, vy)], POWER)

# ---------------------------------------------------------------- mounting holes, outline, labels
for i, (x, y) in enumerate([(4.0, 32.0), (4.0, 58.0), (116.0, 10.0), (116.0, 45.0)]):
    place("MountingHole", "MountingHole_3.2mm_M3", f"H{i + 1}", "M3", x, y)
rect(0, 0, W, H, pcbnew.Edge_Cuts, 0.1)
BS = pcbnew.B_SilkS
text("Bump'em carrier v1 · IBMS Offenburg", 60.0, 38.0, 1.5, BS, bold=True)
text("Teensy 4.1 + MCP4728 → modules A-D", 60.0, 41.0, 1.0, BS)
text("R1-R4 1k series · R5-R8 1M pull-down · D1-D4 BAT85 clamp to 3.3 V", 60.0, 43.5, 1.0, BS)
text("pinout: BumpemServer/docs/diagrams/cabling-4-modules.png", 60.0, 46.0, 1.0, BS)
text("module wires enter here ↓ (bottom edge)", 60.0, 50.0, 1.0, BS)

# ---------------------------------------------------------------- ground pours on both layers + stitching vias in free spots
def seg_dist(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / L))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))

def free(x, y, r):
    for (x1, y1, x2, y2, hw, _) in SEGS:
        if seg_dist(x, y, x1, y1, x2, y2) < r + hw + 0.6:
            return False
    for (cx, cy, cr, _) in DOTS:
        if math.hypot(x - cx, y - cy) < r + cr + 0.6:
            return False
    return 2.0 < x < W - 2.0 and 2.0 < y < H - 7.0

stitch = 0
for gy in [] if PREVIEW else [y / 2 for y in range(8, int(2 * (H - 7)))]:
    for gx in [x / 2 for x in range(4, int(2 * (W - 2)))]:
        if (gx * 2) % 20 == 0 and (gy * 2) % 20 == 0 and free(gx, gy, VIA_D / 2):
            via("GND", gx, gy); stitch += 1

for layer in () if PREVIEW else (pcbnew.F_Cu, pcbnew.B_Cu):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer); z.SetNet(net("GND")); z.SetLocalClearance(mm(0.4)); z.SetMinThickness(mm(0.3))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL); z.SetThermalReliefGap(mm(0.4)); z.SetThermalReliefSpokeWidth(mm(0.5))
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    o = z.Outline(); o.NewOutline()
    for x, y in ((0.5, 0.5), (W - 0.5, 0.5), (W - 0.5, H - 0.5), (0.5, H - 0.5)):
        o.Append(mm(x), mm(y))
    board.Add(z)

# ---------------------------------------------------------------- save board + custom footprint library
os.makedirs(LIB, exist_ok=True)
for fp in () if PREVIEW else (teensy, dac):
    lib_fp = pcbnew.FOOTPRINT(fp)
    lib_fp.SetPosition(P(0, 0)); lib_fp.SetOrientationDegrees(0)
    for pad in lib_fp.Pads():
        pad.SetNetCode(0)
    pcbnew.PCB_IO_KICAD_SEXPR().FootprintSave(LIB, lib_fp)
for fp in board.GetFootprints():
    got = {p.GetNumber(): p.GetNetname() for p in fp.Pads()
           if p.GetNumber() and p.GetNetname() and not p.GetNetname().startswith("unconnected-")}
    assert got == NL.PARTS[fp.GetReference()][3], (fp.GetReference(), got)
board.Save(OUT)

# fill the pours on a board loaded from disk (filling the in-memory board crashes in KiCad 8.0.9)
b2 = pcbnew.LoadBoard(OUT)
pcbnew.ZONE_FILLER(b2).Fill(b2.Zones())
b2.Save(OUT)
print("written", OUT, "stitching vias:", stitch)

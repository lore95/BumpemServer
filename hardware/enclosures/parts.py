"""Printed tower parts. Mounting interface (key + M6 holes) from tower.py; device sizes marked PLACEHOLDER are not measured yet.
Every part is modelled in mounting position: back face (key side) at z = 0, key pointing to -z into the profile slot."""
import cadquery as cq

import tower as P

KEY_W = P.SLOT_OPEN - 2 * P.KEY_CLEAR


def base(length: float, slots: int = 1, width: float | None = None, holes: int = 2, xs: list[float] | None = None) -> cq.Workplane:
    """Plate on one profile face: `slots` = 1 (one slot, plate 24 mm wide) or 2 (both slots, plate covers the face)."""
    width = width or (24.0 if slots == 1 else P.FACE - 4)
    ys = [0.0] if slots == 1 else [-P.SLOT_PITCH / 2, P.SLOT_PITCH / 2]
    part = cq.Workplane("XY").box(length, width, P.PLATE_T, centered=(True, True, False))
    xs = xs if xs is not None else ([0.0] if holes == 1 else [-(length / 2 - 10), length / 2 - 10])
    for y in ys:
        part = part.union(cq.Workplane("XY").box(length, KEY_W, P.KEY_H, centered=(True, True, False)).translate((0, y, -P.KEY_H)))
        for x in xs:
            part = part.cut(cq.Workplane("XY").circle(P.BOLT_HOLE / 2).extrude(P.PLATE_T + P.KEY_H + 2).translate((x, y, -P.KEY_H - 1)))
            part = part.cut(cq.Workplane("XY").circle(P.HEAD_D / 2 + 0.5).extrude(P.PLATE_T).translate((x, y, P.PLATE_T - 1.5)))  # head seat
    return part


def din_rail_mount(length: float = 100.0) -> cq.Workplane:
    """35 mm top-hat rail (EN 60715 TS35x7.5, solid core) on a one-slot plate, for the Futek IAA100's spring DIN clip.
    The IAA100 (FI1573: 66.8 along the rail, 50.4 deep, 17.8 wide, plugs +9.1 at each end) clips on with its plugs up and down."""
    part = base(length, slots=1, width=40.0)
    core = cq.Workplane("XY").box(length, 25.0, 6.5, centered=(True, True, False)).translate((0, 0, P.PLATE_T))
    flange = cq.Workplane("XY").box(length, 35.0, 1.0, centered=(True, True, False)).translate((0, 0, P.PLATE_T + 6.5))
    part = part.union(core).union(flange)
    for x in (-(length / 2 - 10), length / 2 - 10):          # reach the M6 heads through the rail
        part = part.cut(cq.Workplane("XY").circle(P.HEAD_D / 2 + 1).extrude(20).translate((x, 0, P.PLATE_T - 1.5)))
    return part


RS15 = dict(L=62.5, W=51.0, H=28.0, m3_pitch=39.1, m3_from_end=14.65, m3_from_side=25.25)   # Mean Well RS-15 case 971A


def rs15_holder() -> cq.Workplane:
    """Plate for the Mean Well RS-15-24, fixed by its 2 bottom M3 holes (screws from the back, M3 x 6: max 3 mm into the case).
    Screw the supply on first, then bolt the plate to the profile. Mains terminals (AC/L, AC/N, FG) stay exposed: cover them."""
    r = RS15
    ln = r["L"] + 2 * 16                                      # 16 mm each end for the M6 heads
    part = base(ln, slots=1, width=r["W"])
    x0 = -r["L"] / 2                                         # supply centred on the plate, terminal end at -x
    for x in (x0 + r["L"] - r["m3_from_end"], x0 + r["L"] - r["m3_from_end"] - r["m3_pitch"]):
        y = r["m3_from_side"] - r["W"] / 2
        part = part.cut(cq.Workplane("XY").circle(1.7).extrude(20).translate((x, y, -P.KEY_H - 1)))
        part = part.cut(cq.Workplane("XY").circle(3.0).extrude(4.5).translate((x, y, -P.KEY_H)))   # M3 head recess, 3 mm left
    ledge = cq.Workplane("XY").box(3.0, r["W"], 6.0, centered=(True, True, False)).translate((x0 + r["L"] + 1.5, 0, P.PLATE_T))
    return part.union(ledge)                                 # end stop opposite the terminals


RSP = dict(L=295.0, W=127.0, H=41.0,                       # Mean Well RSP-2000 case 952D, wide face ("top view") toward the profile
           holes_a=[(21.0, 18.5), (21.0, 108.5)],           # (from end A, from long edge): M4, max 4 mm deep
           holes_b=[(34.5, 59.0)])                          # from end B (fan end)
GAP = 10.0                                                  # air gap between profile face and supply


def rsp_bracket(end: str = "A") -> cq.Workplane:
    """End bracket for the RSP-2000-48: plate keyed into both slots, M6 holes past the supply end (reachable when mounted),
    raised pad under the supply with M4 x 12 screws from the back into the case holes. Supply end at x = 0, supply over x > 0.
    Assemble: screw the supply onto both brackets first, then bolt the brackets to the profile."""
    r, holes = RSP, (RSP["holes_a"] if end == "A" else RSP["holes_b"])
    pad_len, out_len = 38.0, 24.0                            # pad under the supply / plate beyond its end
    ln = pad_len + out_len
    part = base(ln, slots=2, xs=[-(ln / 2 - out_len / 2)]).translate((ln / 2 - out_len, 0, 0))   # M6 pair at x = -12
    pad = cq.Workplane("XY").box(pad_len, r["W"] - 20, GAP, centered=(False, True, False)).translate((0, 0, P.PLATE_T))
    part = part.union(pad)
    top = P.PLATE_T + GAP
    for fx, fy in holes:
        y = fy - r["W"] / 2
        part = part.cut(cq.Workplane("XY").circle(2.2).extrude(top + 5).translate((fx, y, -P.KEY_H - 1)))
        part = part.cut(cq.Workplane("XY").circle(4.0).extrude(top - 8.0 + P.KEY_H).translate((fx, y, -P.KEY_H)))  # head recess: 8 mm left
    return part


def rsp_box() -> cq.Workplane:
    return cq.Workplane("XY").box(RSP["L"], RSP["W"], RSP["H"], centered=(False, True, False)).translate((0, 0, P.PLATE_T + GAP))


def rsp_bracket_far() -> cq.Workplane:
    """Bracket B in mounting position at the supply's fan end (for renders)."""
    return rsp_bracket("B").mirror("YZ").translate((RSP["L"], 0, 0))


def connector_plate(cut_w: float = 32.0, cut_h: float = 12.0) -> cq.Workplane:
    """Upright panel for the tower's 5-pin signal connector (Phoenix MSTB 2,5/5, 5.08 mm pitch). Cut-out PLACEHOLDER."""
    part = base(50.0, slots=1)
    wall = cq.Workplane("XY").box(50.0, 4.0, 35.0, centered=(True, True, False)).translate((0, 10, P.PLATE_T))
    wall = wall.cut(cq.Workplane("XZ").rect(cut_w, cut_h).extrude(-10).translate((0, 5, P.PLATE_T + 20)))
    for x in (-(cut_w / 2 + 5), cut_w / 2 + 5):              # flange screws
        wall = wall.cut(cq.Workplane("XZ").circle(1.6).extrude(-10).translate((x, 5, P.PLATE_T + 20)))
    return part.union(wall)


def cable_clip(d: float = 8.0) -> cq.Workplane:
    """Clip for one cable along the profile. Diameter PLACEHOLDER."""
    part = base(24.0, slots=1, holes=1)
    ring = (cq.Workplane("YZ").circle(d / 2 + 2.5).circle(d / 2).extrude(12).translate((-16, 0, P.PLATE_T + d / 2 + 1))
            .cut(cq.Workplane("XY").box(30, d * 0.7, 30).translate((-10, 0, P.PLATE_T + d + 4))))  # snap-in opening on top
    return part.union(ring)


def strip_hooks(depth: float = 45.0, h: float = 40.0) -> cq.Workplane:
    """One of two hooks carrying a power strip (no mains parts inside the print). Strip size PLACEHOLDER."""
    part = base(30.0, slots=1)
    arm = cq.Workplane("XY").box(30.0, 5.0, depth, centered=(True, True, False)).translate((0, 0, P.PLATE_T))
    lip = cq.Workplane("XY").box(30.0, h * 0.35, 5.0, centered=(True, False, False)).translate((0, 0, P.PLATE_T + depth - 5))
    return part.union(arm).union(lip)


# name: (builder, status, what it is, still needed)
PARTS = {
    "Slot test plates": (None, "READY TO PRINT", "3 small plates, key clearance 0.1 / 0.2 / 0.3 mm (1/2/3 notches). Sets KEY_CLEAR for all parts.", "nothing"),
    "Base mount plate": (lambda: base(80.0, slots=2), "READY (geometry)", "Covers one face, 2 keys in both slots, 4 M6 holes with head seats. Template for wider parts.", "test-fit result (KEY_CLEAR), bolt length"),
    "IAA100 DIN-rail mount": (din_rail_mount, "READY (datasheet)", "100 mm printed 35 mm top-hat rail on a one-slot plate. The Futek IAA100 clips on (spring DIN clip, FI1573); plugs point up and down along the profile. Alternative: bolt a short steel DIN rail instead.", "check your IAA100 has the DIN clip (66.8 x 50.4 x 17.8 mm version)"),
    "24 V supply plate (RS-15-24)": (rs15_holder, "READY (datasheet)", "Plate under the Mean Well RS-15-24 (62.5 x 51 x 28 mm, case 971A), held by its 2 bottom M3 holes with M3 x 6 screws from the back; end stop opposite the terminals.", "M3 x 6 screws; a cover for the open 230 V terminals (electrician)"),
    "48 V supply brackets (RSP-2000-48)": (lambda: rsp_bracket("A"), "READY (datasheet)", "Two end brackets (A: 2 x M4, B: 1 x M4) under the Mean Well RSP-2000-48 (295 x 127 x 41 mm, 1.95 kg, case 952D). Keyed into both slots; M6 bolts past the supply ends stay reachable; 10 mm air gap behind the supply; fan ends free. Screw the supply onto both brackets first (M4 x 12 from the back, max 4 mm into the case), then bolt them to the profile. Print in ASA or PETG.", "M4 x 12 screws; check the supply's 3 M4 holes on the wide face match (case 952D)"),
    "Signal connector plate": (connector_plate, "CONCEPT", "Upright panel holding the tower's 5-pin MSTB socket: the single signal cable to the breadboard / carrier board.", "MSTB panel part + cut-out size"),
    "Cable clip": (cable_clip, "CONCEPT", "Snap-in clip guiding a cable along the profile (mains, signal, motor).", "cable diameters (PLACEHOLDER 8 mm)"),
    "Power-strip hook (x2)": (strip_hooks, "CONCEPT", "Two hooks carrying the tower's power strip. Holder only, no mains parts inside the print.", "power strip L x W x H"),
}


# ---------- context for the overview renders (not printed) ----------
def profile_block(length: float, slots: int) -> cq.Workplane:
    """Simplified 90x90 slot-10 profile below the part (z < 0), slots lined up with the part's key(s)."""
    yc = 0.0 if slots == 2 else -P.SLOT_PITCH / 2              # one-slot parts sit on the slot at y = 0
    blk = cq.Workplane("XY").box(length, P.FACE, P.FACE, centered=(True, True, False)).translate((0, yc, -P.FACE))
    for dy in (-P.SLOT_PITCH / 2, P.SLOT_PITCH / 2):
        blk = blk.cut(cq.Workplane("XY").box(length + 2, P.SLOT_OPEN, 14.0, centered=(True, True, False)).translate((0, yc + dy, -14.0)))
    return blk


def iaa100_box() -> cq.Workplane:
    """Futek IAA100 envelope (FI1573): 66.8 along the rail, 17.8 wide, 50.4 deep from the rail; plugs 9.1 at each end."""
    body = cq.Workplane("XY").box(66.8, 17.8, 50.4, centered=(True, True, False)).translate((0, 0, P.PLATE_T + 7.5))
    for s in (-1, 1):
        body = body.union(cq.Workplane("XY").box(9.1, 12.0, 20.0, centered=(True, True, False)).translate((s * (66.8 / 2 + 4.55), 0, P.PLATE_T + 7.5 + 25)))
    return body


def rs15_box() -> cq.Workplane:
    r = RS15
    body = cq.Workplane("XY").box(r["L"], r["W"], r["H"], centered=(True, True, False)).translate((0, 0, P.PLATE_T))
    return body.union(cq.Workplane("XY").box(13.0, 40.0, 12.0, centered=(True, True, False)).translate((-r["L"] / 2 - 6.5, 0, P.PLATE_T + 2)))


GREY, AMBER = (0.78, 0.79, 0.80), (0.92, 0.45, 0.35)
CONTEXT = {   # name -> (profile length, slots, [device envelopes])
    "Slot test plates": None,
    "Base mount plate": (120.0, 2, []),
    "IAA100 DIN-rail mount": (140.0, 1, [iaa100_box]),
    "24 V supply plate (RS-15-24)": (130.0, 1, [rs15_box]),
    "48 V supply brackets (RSP-2000-48)": (360.0, 2, [(rsp_bracket_far, (0.55, 0.66, 0.80), 1.0), rsp_box]),
    "Signal connector plate": (90.0, 1, []),
    "Cable clip": (70.0, 1, []),
    "Power-strip hook (x2)": (70.0, 1, []),
}


# ---------- role and mounting steps (printed in the PDFs) ----------
GUIDE = {
    "Slot test plate": (
        "Checks the fit before the real parts are printed: the key on the back must slide into the 10 mm profile slot without "
        "wobbling, the M6 bolt must pass the hole and still grip the T-nut.",
        ["Slide a slot-10 T-nut into a free slot of the tower (or use one already in the slot).",
         "Put the plate on the profile with the key (ridge on the back) in the slot.",
         "Push an M6 button-head bolt through the hole and turn it into the T-nut, hand-tight.",
         "Check: no sideways play, plate flat on the profile, at least ~5 mm of thread in the T-nut.",
         "Report the result: too tight / good / loose (the 0.1 and 0.3 mm plates are in test_fit.stl)."]),
    "Slot test plates": None,
    "IAA100 DIN-rail mount": (
        "Holds the Futek IAA100 force amplifier (now taped) on the tower. The IAA100 has a spring DIN clip on its back; this part "
        "is a short 35 mm DIN rail that bolts into one slot, so the amplifier clicks on and off without screws.",
        ["Choose a slot on the tower face near the load cell cable; slide 2 slot-10 T-nuts into it, about 80 mm apart.",
         "Put the mount on with the key in the slot and the rail facing out; bolt it with 2 M6 bolts through the holes at the ends "
         "(reach them through the openings in the rail).",
         "Hook the top of the IAA100's DIN clip over the rail, press the bottom until it clicks.",
         "Orientation: sensor plug (4-pin) toward the load cell, power/output plug (5-pin) toward the breadboard cable.",
         "To remove: pull the clip's spring tab down (small screwdriver) and tilt the amplifier off."]),
    "24 V supply plate (RS-15-24)": (
        "Holds the Mean Well RS-15-24, the 24 V supply of the force amplifier (now taped). Fixed by the supply's own 2 M3 holes; "
        "an end stop keeps it square.",
        ["Mains first: the supply stays unplugged; its 230 V terminals are wired and covered only by the electrician.",
         "Put the supply on the plate, the end stop against the end opposite the screw terminals.",
         "From the back of the plate, screw 2 M3 x 6 screws into the supply's bottom holes (max 3 mm into the case: no longer screws).",
         "Slide 2 slot-10 T-nuts into a slot; bolt the plate on with 2 M6 bolts through the holes at both ends.",
         "Route the 24 V output (+V, -V) to the IAA100 power plug (pin 1 +Vin, pin 2 GND)."]),
    "48 V supply brackets (RSP-2000-48)": (
        "Hold the Mean Well RSP-2000-48, the motor supply (1.95 kg), on one profile face with a 10 mm air gap. "
        "Bracket A takes the 2 M4 holes at the end without fans, bracket B the single M4 hole at the fan end.",
        ["Supply switched off and unplugged; leave its mains side to the electrician.",
         "Lay the supply with its wide face (the one with 3 M4 holes, case 952D) up. Put bracket A on the end with 2 holes and "
         "bracket B on the fan end, pads on the supply, the bolt flanges pointing away from the supply.",
         "Screw M4 x 12 screws from the back of each bracket into the supply (2 in A, 1 in B); max 4 mm into the case.",
         "Slide 4 slot-10 T-nuts into the tower face: one in each of its 2 slots for each bracket. The two brackets' bolts end up 319 mm apart.",
         "Lift supply + brackets onto the profile, keys in both slots, and bolt each bracket with its 2 M6 bolts. Two people: one holds.",
         "Check: fans and vents free, 10 mm gap behind the supply, output cables (+V, -V) reach the chopper terminals 4 / 5."]),
}
GUIDE["Slot test plates"] = GUIDE["Slot test plate"]

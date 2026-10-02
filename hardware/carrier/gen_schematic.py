"""Generate bumpem-carrier.kicad_sch from netlist.py (net labels on every pin, no-connect flags on unused pins).
Run: python3 gen_schematic.py   (plain Python 3; reads symbols from the installed KiCad 8 libraries)"""
import os
import re
import uuid

import netlist as NL

HERE = os.path.dirname(os.path.abspath(__file__))
KSYM = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols/"
OUT = os.path.join(HERE, "bumpem-carrier.kicad_sch")
ROOT = str(uuid.uuid5(NL.NS, "root-sheet"))
_n = [0]
def uid():
    _n[0] += 1
    return str(uuid.uuid5(NL.NS, f"sch-item-{_n[0]}"))

FONT = "(effects (font (size 1.27 1.27)))"
HIDE = "(effects (font (size 1.27 1.27)) hide)"

# ---------------------------------------------------------------- library symbols
def lib_symbol(lib, name):
    s = open(KSYM + lib + ".kicad_sym").read()
    i = s.find(f'\n\t(symbol "{name}"'); j = s.find('\n\t(symbol "', i + 5)
    blk = s[i:j] if j > 0 else s[i:s.rfind(")")]
    return blk.replace(f'(symbol "{name}"', f'(symbol "{lib}:{name}"', 1)

def pins_of(block):
    """{number: (x, y, angle)} in symbol coordinates (y up)."""
    out = {}
    for m in re.finditer(r'\(pin \w+ \w+\s*\(at ([-\d.]+) ([-\d.]+) ([-\d.]+)\).*?\(number "([^"]+)"', block, re.S):
        out[m.group(4)] = (float(m.group(1)), float(m.group(2)), int(float(m.group(3))))
    return out

def custom_symbol(name, left, right, half_h, ref="U"):
    """left/right: lists of (number, pin name) top to bottom. Passive pins, 2.54 mm pitch."""
    pins = []
    for side, x, ang in ((left, -15.24, 0), (right, 15.24, 180)):
        for i, (num, pname) in enumerate(side):
            y = half_h - 2.54 - 2.54 * i
            pins.append(f'(pin passive line (at {x} {y:.2f} {ang}) (length 5.08) (name "{pname}" {FONT}) (number "{num}" {FONT}))')
    h = half_h
    return (f'(symbol "bumpem-carrier:{name}" (pin_names (offset 1.016)) (exclude_from_sim no) (in_bom yes) (on_board yes)\n'
            f'  (property "Reference" "{ref}" (at 0 {h + 2.54} 0) {FONT})\n'
            f'  (property "Value" "{name}" (at 0 {-h - 2.54} 0) {FONT})\n'
            f'  (property "Footprint" "" (at 0 0 0) {HIDE})\n  (property "Datasheet" "" (at 0 0 0) {HIDE})\n'
            f'  (property "Description" "" (at 0 0 0) {HIDE})\n'
            f'  (symbol "{name}_0_1" (rectangle (start -10.16 {h}) (end 10.16 {-h}) (stroke (width 0.254) (type default)) (fill (type background))))\n'
            f'  (symbol "{name}_1_1" {" ".join(pins)})\n)')

teensy_left = [(str(n), NL.TEENSY_PINS[str(n)]) for n in range(1, 25)]
teensy_right = [(str(n), NL.TEENSY_PINS[str(n)]) for n in range(48, 24, -1)]
dac_left = [(str(n), NL.DAC_PINS[str(n)]) for n in range(1, 7)]
dac_right = [(str(n), NL.DAC_PINS[str(n)]) for n in range(7, 13)]
LIBS = {
    "bumpem-carrier:Teensy41_Socket": custom_symbol("Teensy41_Socket", teensy_left, teensy_right, 31.75),
    "bumpem-carrier:MCP4728_Breakout": custom_symbol("MCP4728_Breakout", dac_left, dac_right, 8.89),
    "Device:R": lib_symbol("Device", "R"),
    "Device:D_Schottky": lib_symbol("Device", "D_Schottky"),
    "Connector:Screw_Terminal_01x05": lib_symbol("Connector", "Screw_Terminal_01x05"),
    "Mechanical:MountingHole": lib_symbol("Mechanical", "MountingHole"),
}
PINS = {k: pins_of(v) for k, v in LIBS.items()}

# ---------------------------------------------------------------- placement (mm, schematic y down)
POS = {"U1": (90.17, 140.97), "U2": (180.34, 74.93)}
for k, m in enumerate(NL.MODS):
    y0 = 50.8 + 57.15 * k
    POS[f"J{k + 1}"] = (386.08, y0)
    POS[f"R{k + 1}"] = (322.58, y0 + 12.7)       # series
    POS[f"R{k + 5}"] = (299.72, y0 + 25.4)       # pull-down
    POS[f"D{k + 1}"] = (299.72, y0 + 2.54)       # clamp
for i in range(4):
    POS[f"H{i + 1}"] = (30.48 + 12.7 * i, 275.59)

items = []
def label(text, x, y, ang):
    just = {0: "left bottom", 180: "right bottom", 90: "left bottom", 270: "right bottom"}[ang]
    just = just.split()[0]
    items.append(f'(global_label "{text}" (shape passive) (at {x:.2f} {y:.2f} {ang}) (fields_autoplaced yes) '
                 f'(effects (font (size 1.27 1.27)) (justify {just})) (uuid "{uid()}") '
                 f'(property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at {x:.2f} {y:.2f} 0) (effects (font (size 1.27 1.27)) hide)))')

for ref, (lib, value, footprint, nets) in NL.PARTS.items():
    X, Y = POS[ref]
    su = NL.sym_uuid(ref)
    pin_entries = " ".join(f'(pin "{n}" (uuid "{uid()}"))' for n in PINS[lib])
    vy = Y + (36.83 if ref == "U1" else 13.97 if ref == "U2" else 6.35 if ref.startswith("J") else 0)
    dy = -5.08 if ref.startswith("D") else 0          # diode: reference and value above the body, clear of the pin labels
    items.append(
        f'(symbol (lib_id "{lib}") (at {X:.2f} {Y:.2f} 0) (unit 1) (exclude_from_sim no) (in_bom {"no" if ref.startswith("H") else "yes"}) (on_board yes) (dnp no) (uuid "{su}")\n'
        f'  (property "Reference" "{ref}" (at {X + 2.54 - (5.08 if dy else 0):.2f} {Y - 1.27 + dy - (34.29 if ref == "U1" else 11.43 if ref == "U2" else 0):.2f} 0) (effects (font (size 1.27 1.27)) (justify left)))\n'
        f'  (property "Value" "{value}" (at {X + 2.54 - (1.27 if dy else 0):.2f} {vy + 1.27 + dy - (2.54 if dy else 0):.2f} 0) (effects (font (size 1.27 1.27)) (justify left)))\n'
        f'  (property "Footprint" "{footprint}" (at {X:.2f} {Y:.2f} 0) {HIDE})\n'
        f'  (property "Datasheet" "~" (at {X:.2f} {Y:.2f} 0) {HIDE})\n'
        f'  (property "Description" "" (at {X:.2f} {Y:.2f} 0) {HIDE})\n'
        f'  {pin_entries}\n'
        f'  (instances (project "bumpem-carrier" (path "/{ROOT}" (reference "{ref}") (unit 1))))\n)')
    for num, (px, py, pang) in PINS[lib].items():
        x, y = X + px, Y - py                       # symbol y is up, schematic y is down
        if num in nets:
            label(nets[num], x, y, {0: 180, 180: 0, 90: 270, 270: 90}[pang])
        else:
            items.append(f'(no_connect (at {x:.2f} {y:.2f}) (uuid "{uid()}"))')

def note(text, x, y, size=1.27):
    items.append(f'(text "{text}" (exclude_from_sim no) (at {x:.2f} {y:.2f} 0) '
                 f'(effects (font (size {size} {size})) (justify left bottom)) (uuid "{uid()}"))')

note("Bump'em carrier board: Teensy 4.1 + MCP4728 DAC -> 4 cable modules (A left, B front, C right, D)", 20.32, 20.32, 2.0)
note("Pins as in firmware/src/main.ino and docs/diagrams/cabling-4-modules.png: enable T27-30, setpoint DAC VA-VD, force T14-17 (A0-A3), I2C T18 SDA / T19 SCL", 20.32, 26.67)
note("Teensy VIN (5 V) is never connected. Teensy and DAC plug into female headers. DAC VCC fed on pad 12; pad 1 (VCC) is the same net on the breakout, left open here.", 20.32, 31.75)
note("Force input protection per module: R1-R4 series (1k) | R5-R8 pull-down (1M, unplugged input reads 0 N) | D1-D4 BAT85 clamp to 3.3 V.", 255.27, 20.32)
note("If the IAA100 output can exceed 3.3 V: R series + R pull-down form a divider (e.g. 0-10 V: 22k / 10k -> 3.1 V). Re-calibrate after any change.", 255.27, 25.4)
note("Terminal pins per module (wire colours): 1 EN yellow, 2 SP+ blue, 3 SP- green, 4 GND white, 5 F brown", 255.27, 30.48)

SCH = f'''(kicad_sch
  (version 20231120)
  (generator "eeschema")
  (generator_version "8.0")
  (uuid "{ROOT}")
  (paper "A3")
  (title_block (title "Bump'em carrier board") (date "2026-10-02") (rev "1") (company "IBMS Offenburg")
    (comment 1 "Generated by hardware/carrier/gen_schematic.py from netlist.py; edit those, not this file"))
  (lib_symbols
{chr(10).join(LIBS.values())}
  )
{chr(10).join(items)}
  (sheet_instances (path "/" (page "1")))
)
'''
open(OUT, "w").write(SCH)

# project symbol library with the two custom symbols, registered in sym-lib-table
lib = "\n".join(LIBS[k].replace('(symbol "bumpem-carrier:', '(symbol "', 1) for k in LIBS if k.startswith("bumpem-carrier:"))
open(os.path.join(HERE, "bumpem-carrier.kicad_sym"), "w").write(
    f'(kicad_symbol_lib (version 20231120) (generator "gen_schematic.py") (generator_version "8.0")\n{lib}\n)\n')
open(os.path.join(HERE, "sym-lib-table"), "w").write(
    '(sym_lib_table\n  (version 7)\n  (lib (name "bumpem-carrier")(type "KiCad")(uri "${KIPRJMOD}/bumpem-carrier.kicad_sym")(options "")(descr "Teensy 4.1 and MCP4728 sockets"))\n)\n')
print("written", OUT)

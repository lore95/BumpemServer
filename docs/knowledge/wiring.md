# Wiring: one Teensy 4.1 + one MCP4728 → four modules

Sources: manual p. 2–3 (§4.2 table); thesis Fig. 7 (one module); `firmware/src/main.ino:27-31` (pin ↔ module); ESCON 70/10 hardware reference Tables 3-17, 3-19 (J5/J6 pins, `escon/`).
Diagram: `docs/diagrams/cabling-4-modules.png`.

## Shared (once)
| From | To | Note |
|---|---|---|
| Teensy **3V** (right edge, 3rd from top) | DAC **VCC** | Never the **5V** pin (top right): leave 5V unconnected |
| Teensy **G** | DAC **GND** | |
| Teensy **19** | DAC **SCL** | |
| Teensy **18** | DAC **SDA** | |
| Teensy **G** | Ground distributor | Common ground for everything below |
| DAC LDAC, RDY | not connected | |
| Teensy USB | lab PC | Powers Teensy + DAC |

## Per module
| Signal | A (left) | B (front) | C (right) | D (out of service) |
|---|---|---|---|---|
| Teensy → ESCON **DigIn2** (enable, **J5 pin 2**) | pin **27** | pin **28** | pin **29** | pin **30** |
| DAC → ESCON **AnIn2+** (setpoint, **J6 pin 3**) | **VA** | **VB** | **VC** | **VD** |
| ESCON **AnIn2−** (**J6 pin 4**) | DAC GND | DAC GND | DAC GND | DAC GND |
| ESCON **GND (Digital I/O)** (**J5 pin 5**) | module's distributor board | ← | ← | ← |
| ESCON **GND (Analog I/O)** (**J6 pin 7**) | module's distributor board | ← | ← | ← |
| IAA100 **Vout** → Teensy (force) | pin **14** (A0) | pin **15** (A1) | pin **16** (A2) | pin **17** (A3) |
| IAA100 **GND** | module's distributor board | ← | ← | ← |
| Distributor board → Teensy **G** | one wire per module (white on the traced driver) | ← | ← | ← |
| 24 V PSU **+V / −V** (Mean Well RS-15-24, 15 W; **4 units, one per amplifier**) | IAA100 Vin / GND | ← | ← | ← |
| 48 V PSU **+V / −V** (Mean Well RSP-2000-48, no power switch) | shunt regulator (maxon 235811) pins **4 / 5** (input); its pins **6 / 7** (output 1) → ESCON **J1** + / − | ← | ← | ← |
| DYMH-103 load cell | IAA100 input | ← | ← | ← |
| Maxon motor + Hall sensors | ESCON J2 motor (1–3 windings, 4 shield) / J3 Hall (1–3 Hall 1–3, **4 +5 V, 5 GND**) | ← | ← | ← |
| ⚠️ Module C found 2026-10-01 | J3 pin 5 (GND) empty → Hall error | | | |

Per module, the Teensy side uses 3 signal wires (enable, setpoint, force) plus grounds.
Grounds: each module has its **own distributor board** in the frame (found 2026-09-30) joining ESCON J5.5, J6.7 and the IAA100 GND;
one wire per module runs from it to Teensy GND. This is the manual's "Distributor".

## Found on the lab cabling (2026-09-30): module C (right)
Tape removed from the J5/J6 cable. Colours below are **at the ESCON end**; the jumper-end colours differ (spliced).

| Set | Jumper end | Wire (ESCON end) | Connected to | Meaning | Plug into (breadboard) |
|---|---|---|---|---|---|
| 3 wires | **black** | yellow | ESCON J5 pin 2 | DigIN2, **enable** | Teensy **29** |
| 3 wires | yellow | pink | nothing | spare | leave unconnected |
| 3 wires | white | black | nothing | spare | leave unconnected |
| 4 wires | **red (female)** | blue | ESCON J6 pin 3 | AnIN2+, **setpoint +** | DAC **VC** (onto the pin) |
| 4 wires | **orange** | green | ESCON J6 pin 4 | AnIN2−, **setpoint −** | DAC GND |
| 4 wires | **blue** | brown | Futek IAA100 "Out" | **force** | Teensy **16** (A2) |
| 4 wires | **purple** | white | module's **distributor board** (ESCON J5.5 + J6.7 + IAA100 GND) | **ground** | Teensy G |

Jumper colours are counter-intuitive (black = enable, purple = ground): **label the jumper ends** before reconnecting.

Matches the per-module table above: all 7 wires accounted for. J6.3 blue / J6.4 green confirmed (the "J5 3/4" report was a typo). Check the Futek terminal of the yellow ground wire is labelled GND.
Module: "right side motor" = C (pulls the subject to the right, `hardware.md`); confirm the viewpoint (subject's right, facing the walking direction).
Still to record: the same trace for modules A, B (and D); colours may differ.

## Not in the sources (look up before wiring)
- ~~ESCON pin numbers~~: model is **ESCON 70/10** (422969); J5/J6 pins above are from its hardware reference (`escon/`). Never connect J5 pin 6 (+5 V) or J6 pins 5–6 (AnOUT, −4…+4 V) to the Teensy.
- Which **wire colour** of the existing jumper cables sits in which J5/J6 position (2 sets per driver: 3 wires + 4 wires, `docs/hardware-photos/`). On the traced driver: 3 go to the ESCON (J5.2, J6.3, J6.4), 1 to the IAA100 Out, 1 to the frame board, 2 are spares (section above). Jumper-end colours still to map.
- IAA100 terminal numbers, and load cell ↔ IAA100 excitation/signal wiring: Futek IAA100 and DYMH-103 datasheets.
- Shunt regulator ↔ ESCON power terminals; motor and Hall cables (Maxon standard cables).
- Which load cell / sensor number belongs to which module (`calibration.md`: assumed S1 = A … S4 = D).

## Power order
- Reading ESCON settings: USB into ESCON J7 first → 48 V on (24 V not needed; enable wire unplugged). 48 V off before unplugging USB.
- Motor test, up: Teensy USB (boots DISARMED) → 24 V (amplifier) → check force reading → 48 V → `bumpem arm`.
- Down: `bumpem release` / `estop` → 48 V off → 24 V off → USB.
- 24 V before 48 V: without the amplifier the Teensy reads 0 N and the closed loop keeps raising the current.

## Power supplies and e-stop (Stanford guide pp. 14–16)
- RSP-2000-48 **−V → shunt pin 5**, **+V → shunt pin 4**, **⏚ → shunt pin 3**; shunt **pins 6/7 → ESCON J1 +/−** (guide p. 16 table, regulator label).
- Shunt regulator DIP: Stanford **55 V = switches 3 and 5 ON** (Vth = 75 V − (4 + 16) × 1 V). IBMS setting unknown.
- Mains side (⏚ L N, 230 V) of both supplies: lab technician only.
- **E-stop** (guide pp. 13–15, Mean Well RSP-2000 datasheet p. 4 + p. 6 in `docs/reference/`):
  - Button with an **SPST-NO** contact block (normally open; Stanford swapped the stock red NC block for a green NO block).
  - Two 24 AWG wires from the contact to the supply's **CN501 pin 7 (Remote ON-OFF)** and **pin 11 (+5V-AUX)**; either wire on either pin.
  - Datasheet: *short* between pin 7 and pin 11 = **power OFF**; *open* = **power ON**. Pressing the button closes the contact → 48 V output off.
  - **Not fail-safe:** a cut wire = open = power stays ON (guide p. 15 warning). **Test before every session.** A fail-safe variant needs extra hardware (e.g. an NC contact driving a relay): ask the technician.
  - CN501 is a Hirose **DF11-12DP** header. Stanford soldered to it; the reversible option is a mating housing **DF11-12DS** with **DF11 crimp terminals** (datasheet p. 6).
  - One RSP-2000 per module means one contact per supply: stack one NO contact block per supply on the same button (keep each pair separate; the control is isolated per unit).
  - The e-stop only switches the 48 V output. Mains and the supply's +5 V/+12 V aux outputs stay live.
- Pressing it removes all rope tension (intended). The GRAIL treadmill e-stop stays the primary stop (`safety.md`).

## Checks (from the 2026-09-29 desk test)
- Remove any loopback jumpers (DAC VA–VD → pins 14–17) before connecting amplifiers.
- Before 24 V / 48 V: continuity per wire, and no continuity between 3V and GND.
- After wiring, with 48 V off: `bumpem arm` → DAC VA–VC ≈ 0.51 V open-loop (kp = kd = 0), enable pins 27–29 high.

## Thesis design check (2026-10-01)
Thesis §2.4/§2.7/§2.8 per module: ESCON motor driver, brake chopper (= maxon shunt regulator), 48 V supply (one per module), load cell + Futek IAA100, **24 V supply for the IAA100 only** (§2.7), distributor (common ground). Shared: Teensy 4.1 + MCP4728. Encoder: not used (§7 lists it as future work). E-stop: thesis mentions only the treadmill's.
The thesis does not describe the Hall sensor wiring. maxon/ESCON documents put Hall GND on ESCON J3 pin 5, which is empty on two modules (2026-10-01).

## Motor connector → ESCON (maxon EC 90 flat 500267 = V1, catalog p. 327, `docs/reference/maxon-500267-catalog-page.pdf`)
One 8-pin Molex 46015-0806 on the motor:
| Motor pin | Signal | ESCON |
|---|---|---|
| 1 | Hall sensor 1 | J3 pin 1 |
| 2 | Hall sensor 2 | J3 pin 2 |
| 3 | VHall 4.5–24 VDC | J3 pin 4 (+5 V) |
| 4 | Motor winding 3 | J2 pin 3 |
| 5 | Hall sensor 3 | J3 pin 3 |
| 6 | GND (Hall) | J3 pin 5 |
| 7 | Motor winding 1 | J2 pin 1 |
| 8 | Motor winding 2 | J2 pin 2 |
J2 pin 4 = cable shield (no signal).

**Module C found (2026-10-01):** J2 = red, brown, white + **blue on pin 4 (shield)**; J3 = yellow, pink, grey, green, **pin 5 empty**. 8 wires for 8 motor pins → the **blue wire is most likely the Hall GND (or VHall) on the wrong terminal**. Same on a second module. Confirm at the motor connector (colour per pin), then move blue J2.4 → J3.5 if it is motor pin 6.

**Module C motor connector, read from the wire side (2026-10-01):** top row L→R brown, red, blue, grey; bottom row L→R white, green, pink, yellow.
Mirrored numbering (wire side): yellow 1 Hall 1, pink 2 Hall 2, green 3 VHall, white 4 winding 3, grey 5 Hall 3, **blue 6 GND**, red 7 winding 1, brown 8 winding 2.
Matches the ESCON wiring for 7 of 8 wires (J2: red/brown/white = windings 1/2/3; J3: yellow/pink/grey/green = Hall 1/2/3/+5 V). **Blue = Hall GND, sits on J2 pin 4 (shield) → move to J3 pin 5.** Assumes colours continuous motor → ESCON (consistent with all other wires).
**Fixed 2026-10-01:** module C blue (Hall GND) moved J2 pin 4 → **J3 pin 5** → ESCON LED **green**, Hall error gone. J2 pin 4 now empty (shield, unused). Apply the same check/fix to every module.

## Breadboard wire colours (convention from 2026-10-02)
For wires placed on the breadboard: **black = GND** (incl. Teensy G → blue − rail, pin 16 → rail), **red = 3.3 V**, **yellow = SCL**, **blue = SDA**, other colours = module signals. Red + rail stays empty.
Do not copy thesis Fig. 7 (it uses red for ground). The ESCON harness jumpers keep their own colours and do **not** follow this (black = enable, purple = GND, red = SP+, orange = SP−, blue = force): label their ends.
Actual breadboard (2026-10-02): **− rail** = T G, D GND, T 16 (short wire), module C purple (GND), orange (SP−); **+ rail** = T 3V, D VCC (3.3 V only, labelled); direct: T 19 → D SCL (**purple**), T 18 → D SDA (**white**), T 29 ← black (enable), D VC ← red (SP+). ⚠️ Two purple wires near the Teensy (SCL and module C GND): label them.

## Recabling plan (2026-10-02): one colour from ESCON to breadboard
The jumper extensions are replaced so each wire keeps its ESCON-side colour. Per module: **yellow = enable** (J5.2 → T 27 / T 29), **blue = setpoint +** (J6.3 → D VA / D VC, needs a **female end**), **green = setpoint −** (J6.4 → − rail), **white = ground** (distributor → − rail), **brown = force** (IAA100 Out → T 14 / T 16 later; not plugged now), pink + black = spares (taped).
⚠️ SDA (T 18 → D SDA) is also white: label it or change it to grey. Drawing: `docs/diagrams/cabling-4-modules.png`.

**Module A J3 (2026-10-02): green and grey were swapped** (Hall supply ↔ Hall 3) → strong uncontrolled pull. Correct for every module: J3 1 yellow, 2 pink, 3 grey, 4 green, 5 blue; J2 1 red, 2 brown, 3 white, 4 empty. Check J2/J3 on every module against this before first drive.

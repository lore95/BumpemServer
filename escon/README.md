# ESCON configuration

**Model: maxon ESCON 70/10, part 422969** (label on the driver, photo `docs/hardware-photos/2026-09-29_escon-7010-connectors.jpg`).
Hardware reference: `ESCON-70-10-Hardware-Reference-rel9079.pdf` (maxon, 2021-08).

## I/O pins used by Bump'em (hardware reference Tables 3-17, 3-19)
| Connector | Pin | Signal | Bump'em use |
|---|---|---|---|
| J5 Digital I/O | 1 | DigIN1 | not used by the manual's wiring |
| J5 | **2** | **DigIN2** | enable ← Teensy 27/28/29/30 |
| J5 | 3, 4 | DigIN/DigOUT3, 4 | not used |
| J5 | **5** | **GND** | → ground distributor |
| J5 | 6 | +5 VDC aux out (≤ 10 mA) | **never to a Teensy pin** |
| J6 Analog I/O | 1, 2 | AnIN1+ / AnIN1− | not used by the manual's wiring |
| J6 | **3** | **AnIN2+** | setpoint ← DAC VA/VB/VC/VD |
| J6 | **4** | **AnIN2−** | → DAC GND |
| J6 | 5, 6 | AnOUT1, AnOUT2 (−4…+4 V) | **never to a Teensy pin** (negative voltage) |
| J6 | **7** | **GND** | → ground distributor |

Levels (§3.3.5–3.3.6): DigIN logic 1 > 2.4 V typ. (Teensy 3.3 V is enough), logic 0 < 1.0 V, switching delay < 8 ms.
AnIN ±10 V differential, 12-bit, 5.64 mV resolution (DAC 0–3.3 V is inside the range).

## Stanford reference configuration (`stanford/ESCON_Current_Ctrl_Config.edc`)
Downloaded 2026-09-30 from the "Config" link on https://biomechatronics.stanford.edu/bump-em (same Drive ID as manual §4.3.1).
Created 03.03.2020 for an **ESCON 70/10** with a maxon EC motor (Stanford: EC90 flat). Decoded values:
| Parameter | Value |
|---|---|
| Mode of operation | Current controller (speed limiter on) |
| Digital inputs configuration 0x00000010 | **DigIN2 = Enable**; DigIN1, 3, 4 = None |
| Analog inputs configuration 0x00000010 | **AnIN2 = Set value**; AnIN1 = None |
| Set value current | **0 V → 0 A, 10 V → 30 A (3 A/V)** |
| Max. output current limit / nominal current | 30 A / 4.06 A |
| Motor | maxon EC, 11 pole pairs, speed constant 42.1 rpm/V, 0.904 Ω, 0.892 mH, max 1960 rpm |
| Motor torque constant (tuning data) | 226.8 mNm/A |
| Analog outputs | not configured |

Nibble decoding (4 bits per input) is consistent with the manual on both fields (enable on DigIN2, setpoint on AnIN2).

**Conflict to resolve:** if the IBMS drivers carry this file (manual says to load it), the DAC's 0–3.3 V gives **0–9.9 A**, not 0–30 A as the firmware assumes (`i_full = 30`). Firmware current values are then 3.03× the real current. See `docs/STATUS.md`.

## Still to record
- ESCON Studio parameter file: not found. It can be **read back from each driver** with ESCON Studio (Windows, USB J7) and saved here. That also answers the next three lines.
- AnIN2 scaling (voltage ↔ current setpoint). Firmware assumes 3.3 V ↔ 30 A (`i_full`, `legacy/Arduino_Script.ino:242`).
- Current limit per module; which DigIN is configured as enable and which AnIN as setpoint (the manual says DigIN2 / AnIN2).
- Module (A/B/C/D) ↔ controller serial number ↔ last auto-tune date.

## Status LED (hardware reference p. 28, Table 3-23)
| Green | Red | Meaning |
|---|---|---|
| off | off | init |
| slow blink | off | disabled (ready, enable input low) |
| on | off | enabled |
| 2× | off | stopping / standstill |
| off | 1× | +Vcc over-/undervoltage, +5 V undervoltage |
| off | 2× | thermal overload, overcurrent, power stage protection, internal hardware |
| off | 3× | encoder / DC tacho cable break or polarity |
| off | 4× | PWM set value input out of range |
| off | 5× | Hall sensor pattern / sequence / frequency |
| off | on | auto-tuning identification, internal software |

Module C, 2026-10-01: **red steady, green off** = Auto Tuning Identification Error **or** Internal Software Error (Table 3-23, p. 29). Power stage off. Exact error to be read in ESCON Studio (status window). Do not run Regulation Tuning or a firmware update before diagnosing.

Module C, 2026-10-01 (later): red 1× (supply) error cleared after rework at J1, then **red 5× → ESCON Studio: "Hall Sensor Pattern Error: combination of Hall sensor signals invalid"**. Studio now connects.
J3 Hall plug (hardware reference Table 3-12): 1 Hall 1, 2 Hall 2, 3 Hall 3, 4 +5 V Hall supply (≤ 30 mA), 5 GND. Inputs have 2.7 kΩ pull-ups (p. 16): an unconnected Hall wire reads high.
Module C Controller Monitor (2026-10-01): Current Controller, DI2 = Enable, AI2 = Set Value, offset 0.0070 A, rotor position by digital Hall sensors, all other I/O unused → **matches the Stanford config** (`stanford/`). Caveat: an accidental Download on 2026-09-30 may have loaded that file. Config is not the cause of the Hall error.
ESCON Studio Diagnostics, module C (2026-10-01): motor test OK (motor turned → windings and power stage working). **Hall sensor connection test FAILED**; all three Hall states frozen while turning the drum by hand. Likely: Hall wires or Hall supply (+5 V / GND, J3 pins 4/5) broken or not connected; less likely: Hall sensors damaged. Next: J3 re-seat, cable inspection, J3 pin 4–5 ≈ 5 V, continuity J3 → motor.
**Cause found (2026-10-01): module C's J3 has wires only on pins 1–4; pin 5 (Hall GND) is empty** → Hall sensors unpowered → frozen signals, pattern error. Fix: identify the Hall cable's GND conductor from the motor's colour code (motor label → maxon datasheet), check pins 1–4 order, then connect GND to pin 5. Do not guess.
J3 (2026-10-01 photo): 1 yellow, 2 pink, 3 grey, 4 green, 5 empty; extension wires spliced under tape below J3 (pink is not a maxon Hall colour). maxon's internal Hall order is GND before +V Hall, ESCON J3 is +5 V (4) then GND (5): pin 4 may carry either. Identify via splice + motor datasheet before connecting pin 5.
**Motor model check:** maxon EC 90 flat 323772 (24 V) has 12 pole pairs, 135 rpm/V; the Stanford config says 11 pole pairs, 42.1 rpm/V → Stanford motor is another variant. Module C's motor label needed before any config download.
**Second module (2026-10-01): same J3 wiring (pin 5 empty) and same Hall error** → systematic, not a broken wire. Hypotheses: the Hall supply (GND or +V) was taken from the **distributor board** or from the **24 V supply** (RS-15-24, found disconnected). Check where the RS-15-24 outputs go and the motor's Hall supply range (datasheet, needs motor label).
Thesis check (2026-10-01): 24 V supply powers only the IAA100 (§2.7) → not the Hall supply. Hall wiring not described in the thesis; per maxon/ESCON docs, Hall GND belongs on J3 pin 5. Next: splice below J3, distributor board, motor label.
Motor identified (2026-10-01): **maxon EC 90 flat 500267** (260 W, 48 V, 11 pole pairs) → the Stanford config fits; no reload needed for the motor data. Hall colour code: from its catalog page (pending). maxon usually lists Hall GND before VHall; ESCON J3 has +5 V on 4, GND on 5 → J3 pin 4's green wire may be either. Do not connect pin 5 before checking.
Catalog page (2026-10-01): EC 90 flat 500267 = V1, 8-pin connector (Hall GND pin 6, VHall pin 3, 4.5–24 V). Module C: J2 has 4 wires (red, brown, white, **blue on shield pin 4**), J3 has 4 → 8 total = all motor pins present; **blue on J2.4 is most likely the Hall GND** → belongs on J3 pin 5. Confirm at the motor connector first.
Motor connector read (2026-10-01, mirrored wire-side numbering): blue = motor pin 6 = Hall GND, wired to J2 pin 4 (shield) instead of J3 pin 5; all other 7 wires correct. Fix: move blue to J3 pin 5. Possible reason it worked before: shield terminal → housing/earth → indirect ground path via Teensy/PC (unverified).
**Module C fixed (2026-10-01):** blue (Hall GND) moved from J2 pin 4 to J3 pin 5 → LED green, no error.
Module C Diagnostics after the fix (2026-10-01): **all tests passed**; LED green blinking (DISABLE, ready).

## Module A (left) driver configuration: `moduleA_left_2026-10-01.edc` (uploaded 2026-10-01)
= Stanford config **plus auto-tuning results**. Identical: motor data (11 pole pairs, 4.06 A nominal, 30 A limit, 1960 rpm), current-controller mode, DigIN2 = enable, AnIN2 = set value, **set value 0–10 V → 0–30 A**, offset 0.0070 A, Hall rotor detection.
26 values differ, all tuning/identification results: R 0.909 Ω, L 0.947 mH, rotor inertia, current controller P gain 186 / integral time 1041 µs (Stanford 170 / 20000), speed controller gains, Hall averaging. → auto-tuning was run after loading the Stanford file (manual §4.3.1 step 6).
**Confirms the scaling mismatch** for this driver: DAC 3.3 V = 9.9 A, firmware assumes 30 A (`i_full`).
Module C: upload still to do; if its gains equal the Stanford file (e.g. integral time 20000 µs), the accidental Download overwrote the tuning → re-run auto-tuning.

**Module A (2026-10-02): first open-loop test pulled far too strong** (same settings as C, which was gentle). Cause found: **A's J3 green and grey swapped** (green = Hall supply on pin 3, grey = Hall 3 on pin 4) → Hall supply into Hall-3 output, wrong commutation. Fix: J3 = 1 yellow, 2 pink, 3 grey, 4 green, 5 blue (as C). Then Diagnostics on A (Hall test must pass: sensor 3 was tied to +5 V while swapped) before driving again.

# Makerspace list (next visit)

Written 2026-11-16. Tick what you have. Skip anything already soldered on your board.

## 1 · Carrier board v1 (the PCB from the maker)
Guide: `hardware/carrier/fab/bumpem-carrier-soldering.pdf`. As built (D23): **1 MΩ in the D1–D4 places, not BAT85; R5–R8 stay empty.**

| ☐ | Qty | Part | Goes to | German drawer / search term |
|---|---|---|---|---|
| ☐ | 4 | resistor 1 kΩ, 0.25 W, 1 %, axial | R1–R4 | "1 K" (brown-black-black-brown-brown) |
| ☐ | 4 | resistor 1 MΩ, 0.25 W, 1 %, axial | D1–D4 places (pull-up to 3.3 V) | "1 M" (brown-black-black-yellow-brown) |
| ☐ | 2 | female header 1 × 24, 2.54 mm (or cut from 1 × 40) | Teensy socket | "Buchsenleiste 1x24 2,54" |
| ☐ | 2 | female header 1 × 6, 2.54 mm | DAC socket | "Buchsenleiste 1x6 2,54" |
| ☐ | 4 | Phoenix MSTB 2,5/5-GF-5,08 (1776537), board header | J1–J4 | — |
| ☐ | 4 | Phoenix MSTB 2,5/5-STF-5,08 (1778014), cable plug | one per module cable | — |
| ☐ | 4 | M3 spacer + M3 screw | board corners → carrier plate | "Abstandsbolzen M3" |
| ☐ | 20 | wire-end ferrules 0.25–0.5 mm² | module wires into the plugs | "Aderendhülsen 0,5 mm²" |
| ☐ | 2 | male pin strip 1 × 24 (spare) | keeps the sockets straight while soldering (not soldered in) | "Stiftleiste 1x40" |

## 2 · Other project (not Bump'em): LED circuit on a breadboard
From that project's own guide (resistor R3 = 150 Ω). Only the parts below; the rest is in that guide.

| ☐ | Qty | Part | Note |
|---|---|---|---|
| ☐ | small pack | "2N2222A TO-92" | transistor |
| ☐ | small pack | "LED 5mm rot" | |
| ☐ | 1 | **5 V supply, pick ONE:** | |
| ☐ | | a) "MB102 Breadboard Netzteil Modul" + any USB charger | plugs straight onto the breadboard rails (easiest). Set the jumper to **5 V**. |
| ☐ | | b) "Batteriehalter 3x AA mit Kabel" + 3 AA batteries | 4.5 V: R3 stays 150 Ω, nothing in the guide changes |

## 3 · Other jobs that need a soldering station (if time)
| ☐ | Part | For |
|---|---|---|
| ☐ | 🔴 e-stop: 2 BACO boxes found (2026-11-16), each with **2 green NO blocks (3-4)**, own red + black pair per block. One box = 2 supplies only, and one press must stop all 4 → plan below (ask the technician to check it) | TODO 1 |
| ☐ | 1 × BACO **NC** contact block (red, terminals 1-2), same series as the green ones | in ONE box: opens on press or a cut wire (fail-safe) |
| ☐ | 1 × relay, **24 V DC coil, 4 changeover contacts, gold-flashed contacts** (e.g. Finder 55.34.9.024 gold version) + its screw socket + coil module (diode + LED) | its 4 NC contacts short CN501 pin 7 + 11 of each supply when the coil drops |
| ☐ | 4 × Hirose DF11-12DS housing + 8 DF11 crimp terminals 24–28 AWG (+ spares), crimp tool | plug onto CN501 of each RSP-2000 |
| ☐ | 2-core cable 0.25 mm²: button → relay, relay → each tower; a 2-pin inline connector per tower (towers stay movable); small box for the relay | e-stop |
| ☐ | cable gland / strain relief, labels A–D on each pair | e-stop |
| ☐ | 1.5 mm² fine-stranded wire + insulated ferrules + crimp tool | 🔴 tower B chopper → ESCON cable, TODO 1 |
| ☐ | thin wire 0.14–0.25 mm² | optional hardware sync on Teensy pin 2 (TODO "Later"); only once the Vicon sync output is known |

## Bring
Multimeter (beep checks), solder + flux, desoldering wick, side cutters, the soldering guide PDF, the Teensy and DAC (to check the socket fit after soldering, not during).

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
| ☐ | 4 + 2 spare | Phoenix MSTB 2,5/5-GF-5,08 (1776537), board header: **again, the first ones melted while soldering** | J1–J4 | — |
| — | — | Phoenix MSTB 2,5/5-STF-5,08 cable plugs: **already have them, don't buy** | | |
| — | — | M3 × 16 screws + M3 nuts for the printed carrier plate: **already have them, don't buy** | board corners → carrier plate | |
| — | — | wire-end ferrules 0.5 mm²: **already have them, don't buy** (20 needed) | module wires into the plugs | "Aderendhülsen 0,5 mm²" |
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
| ☐ | 🔴 e-stop, two-box version (user's choice 2026-11-16, no relay): the 2 BACO boxes as they are, each green NO block (3-4) → one supply: box 1 → A + B, box 2 → C + D. Not fail-safe, one box stops 2 towers: mount side by side, label "PRESS BOTH", test before every session. Technician to agree | TODO 1 |
| ☐ | 4 × Hirose DF11-12DS housing + 8 DF11-2428SC crimp terminals (+ spares). **Probably not at the makerspace:** ask, else Reichelt / Mouser (or pre-crimped DF11 leads, no tool needed) | plug onto CN501 of each RSP-2000, places 7 + 11 |
| ☐ | fine crimp tool for DF11 (e.g. Engineer PA-09), unless pre-crimped leads | e-stop |
| ☐ | 2-core cable 0.25 mm², long enough from each box to its 2 towers (measure in the lab) | e-stop |
| ☐ | 4 × locking 2-pin plug, one per tower (towers stay movable) | e-stop |
| ☐ | board / plate to mount both boxes side by side, cable glands, labels A–D and "PRESS BOTH" | e-stop |
| ☐ | 1.5 mm² fine-stranded wire + insulated ferrules + crimp tool | 🔴 tower B chopper → ESCON cable, TODO 1 |
| ☐ | thin wire 0.14–0.25 mm² | optional hardware sync on Teensy pin 2 (TODO "Later"); only once the Vicon sync output is known |

## Bring
Multimeter (beep checks), solder + flux, desoldering wick, side cutters, the soldering guide PDF, the Teensy and DAC (to check the socket fit after soldering, not during).

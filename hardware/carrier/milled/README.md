# Carrier board, makerspace version (single-sided)

For the HS Offenburg makerspace's PCB mill: one copper layer, no plating, no solder mask, no copper fill.
Same outline, mounting holes and Teensy / DAC / plug positions as v1 (`../`), so the printed carrier plate fits and every cable plug goes in the same place.

**To make it:** send `fab/bumpem-carrier-milled.zip`. Its `gerbers/` folder is what the mill needs (bottom copper, outline, one drill file with all 114 holes, `MAKERSPACE.txt` in German and English: mill the bottom only, remove the unused copper, drill every hole). The PDFs are the 1:1 bottom view, the parts placement and the soldering guide.

## Why it is easier to solder
- **Everything is soldered on the bottom**: 70 joints, nothing on the top, no vias.
- **No ground fill**: around each pad there is bare board, so solder that misses the pad does not stick. Ask the makerspace to remove the unused copper (rub-out); otherwise isolation ≥ 0.6 mm.
- **Unused socket pins are bare holes** (no copper): nothing to solder, nothing to short. VIN cannot touch anything.
- **7 wire links** (W1–W7, insulated wire on the top, soldered underneath) instead of vias: W1 SDA, W2 SCL (crosses W1), W3 3.3 V, W4 enable B, W5–W7 setpoint A–C.
- The **1 kΩ resistors bridge tracks** too (their bodies cross the tracks between their pads). R2 has 15.24 mm leg spacing.
- Copper letters A–D next to each plug (bottom side).

## Circuit (differences from v1, D24)
Same pins as v1 (`../netlist.py`): Teensy 27–30 enable, 14–17 force, 18/19 I²C, DAC VA–VD setpoints.
Force input: plug pin 5 → 1 kΩ → Teensy pin; **1 MΩ from plug pin 5 to the same module's enable line** (plug pin 1). Armed (enable high) a loose force cable reads ≈ 200 N → that motor 0 A and over-force FAULT, as the v1 board as built (D23); disarmed it reads 0 N. No diodes, no pull-down. With the amplifier connected the 1 MΩ changes nothing measurable.
DAC ground through its row-1 GND pin only (both GND pins are joined on the breakout).

## Layout (hand-planned, `gen_milled.py`)
Ground runs round the outside: left edge, a bus under the plugs (pins 3 and 4 from below), right edge, top edge to the DAC.
Force lines go up over the Teensy's far row (F_D outermost) and come down between the Teensy and the DAC in A–D order; I²C and 3.3 V run under the Teensy and cross them on W1–W3.
Below: lanes top → bottom SP_D, EN_A, F_D, F_C, F_B, EN_D, EN_C, SP_A, FIN_A, SP_B; jumps: R1 over EN_D EN_C SP_A, R2 over EN_D EN_C SP_A SP_B, R3 over EN_D, R4 over SP_D, W5/W6 over F_D F_C EN_D EN_C, W7 over F_D F_C EN_D, W4 over SP_A FIN_A; the pull-ups R5–R8 bridge each plug's setpoint track.
(`gen_milled.py` also holds a grid router with wire-link moves; it is not used for the final layout: greedy routing needed 7–17 links and boxed nets in.)

## Build and check
`./build_milled.sh` (KiCad 8; `python3` with matplotlib for the guide): generates the board, runs DRC (must print 0 violations; the 7 "unconnected" items are W1–W7, which KiCad cannot see as wires), runs `check_milled.py` (every net one piece, counting the wire links: must print "all connected"), writes `fab/`.

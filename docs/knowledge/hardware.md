# Hardware

Sources: `docs/thesis/thesis.pdf` §2.3–2.9, §3.1; `docs/thesis/manual.pdf` §3, §4.2; `legacy/Arduino_Script.ino:47-64`.

## Modules
| Module | Letter | Direction (thesis Fig. 11) | Force pin | Enable pin (ESCON DigIn2) | DAC ch |
|---|---|---|---|---|---|
| 1 | A | left  | A0 (pin 14) | 27 | A |
| 2 | B | front | A1 (pin 15) | 28 | B |
| 3 | C | right | A2 (pin 16) | 29 | C |
| 4 | D | not stated (presumably back) | A3 (pin 17) | 30 | D |

Diagonals: `ab` = front-left, `bc` = front-right (thesis Fig. 11 d/e). `cd`, `da` exist in firmware, untested.

**Module 4 status: out of service.** Thesis §7 says "mechanical damage"; manual §2 says "a new motor driver needs to be purchased". Resolve which is true.

## Per-module chain
Teensy 4.1 → I²C (SDA 18, SCL 19) → MCP4728 DAC (12-bit, 0–3.3 V) → ESCON 70/10 AnIn2 (J6.3) → Maxon BLDC (EC) motor → reel drum → rope → DYMH-103 load cell → Futek IAA100 → Teensy ADC.

## Motor (all modules' labels, 2026-10-01)
**maxon EC 90 flat Ø90 mm, 260 W, 48 V, with Hall sensors, part 500267** (maxon product page): 11 pole pairs, no-load speed 1960 rpm, torque constant **231 mNm/A**, speed constant 41.3 rpm/V, terminal resistance 0.844 Ω, inductance 1.07 mH, stall current 56.9 A. Matches the Stanford ESCON config (11 pole pairs, 1960 rpm, 226.8 mNm/A). Firmware `kt = 0.1524` differs (see STATUS).
Hall colour code: catalog page PDF (to be added to `docs/reference/`).

## Power
- 48 V DC per module → shunt regulator / brake chopper → ESCON (thesis §2.4).
- 24 V DC → IAA100.
- Common ground via distributor. Logic 3.3 V.

## Sensing
- Load cell DYMH-103. Thesis Table 1 says 100 kg max; text says 1000 N (§3.1) / 980 N (§8). Excitation 10 V, sensitivity 1.6 mV/V.
- IAA100 gain set via DIP switches + zero/span pots: 0–3.3 V ↔ 0–200 N (§3.1–3.2).
- Teensy ADC 10-bit (`ADCresolution = 1023`, `.ino:39`).

## Mechanical
- 80×80 mm aluminium profiles, floor mounts, height adjustable to CoM (§2.9).
- Breakaway cable per rope (§2.1).
- No reflective parts (mocap) (§2.3).

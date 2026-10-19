# Hardware

Sources: `docs/thesis/thesis.pdf` §2.3–2.9, §3.1; `docs/thesis/manual.pdf` §3, §4.2; `legacy/Arduino_Script.ino:47-64`.

## Modules
| Module | Letter | Direction (thesis Fig. 11) | Force pin | Enable pin (ESCON DigIn2) | DAC ch |
|---|---|---|---|---|---|
| 1 | A | left  | A0 (pin 14) | 27 | A |
| 2 | B | front | A1 (pin 15) | 28 | B |
| 3 | C | right | A2 (pin 16) | 29 | C |
| 4 | D | back (not in the thesis; confirmed by the project lead 2026-10-02) | A3 (pin 17) | 30 | D |

Diagonals: `ab` = front-left, `bc` = front-right (thesis Fig. 11 d/e). `cd`, `da` exist in firmware, untested.

**Setup 2026-10-02:** A (left), C (right) and D (back) mounted and run in the open-loop test; B (front) not installed. Earlier, D was out of service (thesis §7: "mechanical damage"; manual §2: "a new motor driver needs to be purchased"). Firmware still boots with `ch_D = 0`: `bumpem set ch_D 1` after each power-up.

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
- **Found 2026-10-05:** a 4th IAA100 still paired with a **DYMH-103 200 kg, 1.0 mV/V** (others: 100 kg, 1.6 mV/V) → ~3× less signal per N, so ~3× more noise and ±0.3 % of 1962 N ≈ ±6 N. Possibly thesis sensor S4 (calibration.md). Check with 6 / 8 / 12 kg before use; small errors → firmware `gain_X` / `offset_X`. **It is on tower B (front)** (project lead, 2026-10-19); A, C, D have 100 kg cells. Check: IAA100 can be trimmed to 200 N → 3.3 V with it (~1 mV input at full scale); noise at rest vs A / C / D (closed loop holds 2 N, the PD's derivative amplifies noise). Cleanest fix: a matching 100 kg DYMH-103.
- Load cell DYMH-103. Thesis Table 1 says 100 kg max; text says 1000 N (§3.1) / 980 N (§8). Excitation 10 V, sensitivity 1.6 mV/V.
- IAA100 gain set via DIP switches + zero/span pots: 0–3.3 V ↔ 0–200 N (§3.1–3.2).
- Teensy ADC 10-bit (`ADCresolution = 1023`, `.ino:39`).

## Mechanical
- 80×80 mm aluminium profiles, floor mounts, height adjustable to CoM (§2.9).
  **Actual (2026-10-07):** **90×90 light, B-type (Bosch-compatible, 45 grid), slot 10**: 8 open grooves (2 per face), groove 10 mm wide / 14 mm deep, 4 star-shaped core bores (for M12), large hollow centre. Identified from a top photo (`docs/hardware-photos/IMG_9801.heic`); maker unknown, not item (item's own system is slot 8). Sold e.g. as Motedis "Aluprofil 90x90 L B-Typ Nut 10". Measured: face 90 mm, slot cavity ~10–30 mm from the edge, T-nut head 20 mm; parts held with ISO 7380 button-head screws (class 010.9) in slot-10 T-nuts. Thesis value 80×80 is outdated. Bolt thread: to measure.
- Breakaway cable per rope (§2.1).
- **Reel drum:** measured in Stanford's `Reel Drum.STEP` (CAD from biomechatronics.stanford.edu/bump-em, local copy `docs/reference/stanford-cad/`, 2026-10-19): rope surface **38.10 mm** (radius 19.05 mm = firmware `rc`, build guide p. 34), flanges 63.5 mm, drum height 34.3 mm, rope tie hole **5.59 mm** (radial, through the core). IBMS drums are printed from this file (project lead, 2026-10-15) → same unless scaled; one caliper check confirms it.
- **Rope:** Stanford BOM = braided Kevlar string, 100 ft, 500 lb (≈ 2.2 kN); **diameter stated nowhere** (guide, BOM, thesis, manual). IBMS rope diameter unknown (2026-10-15). The drum's 5.59 mm tie hole limits it: **~2–3 mm** passes the hole and its figure-eight knot still stops (3 mm proposed by the project lead fits). The eyebolt is a McMaster part (`McMC Eyebolt.SLDPRT`, not readable here): check its eye by hand. At 3 mm the rope winds at ~20.6 mm radius, ~8 % above `rc` → ~8 % less force per A in open loop; the closed loop corrects it. Choose low-stretch (Dyneema / Kevlar), ≥ ~2 kN, well above the breakaway. A thicker rope winds at a larger radius than `rc` → slightly less force per A in open loop.
- No reflective parts (mocap) (§2.3).

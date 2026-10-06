# Broken tower: unpowered diagnosis

The tower listed as out of service in the thesis (48 V supply and brake chopper suspected shorted, before 2026-10).
Everything unplugged from mains, Teensy and other modules. Meter: **Ω** = resistance mode, **▶|** = diode mode.
**OL** (or `0L`, `1`) = open, no connection. Always write the unit shown (Ω, kΩ, MΩ, V).
"Rising" = the value keeps climbing (capacitors charging): write where it is after ~10 s.

## 0. Meter
| # | Mode | Red | Black | Expected | Result |
|---|---|---|---|---|---|
| 0a | Ω | probes touching | | ~0 Ω | 0 |
| 0b | Ω | probes in the air | | OL | OL |
| 0c | ▶| | probes touching | | ~0 | 0 |
| 0d | ▶| | probes in the air | | OL | OL |

## 1. Brake chopper (shunt regulator, maxon 235811), all wires off its terminal block
| # | Mode | Red | Black | Expected (healthy) | Result |
|---|---|---|---|---|---|
| 1a | Ω | pin 4 (+V in) | pin 5 (−V in) | rising, not ~0 | rising, 30 kΩ at 20 s |
| 1b | Ω | pin 5 | pin 4 | a value, not ~0 | falling, MΩ range |
| 1c | Ω | pin 6 (out) | pin 7 (out) | rising or a value, not ~0 | rising, kΩ |
| 1d | Ω | pin 4 | pin 3 (⏚) | OL | OL |
| 1e | Ω | pin 5 | pin 3 (⏚) | OL | OL |
| 1f | Ω | pin 4 | metal housing / heat sink | OL | OL |
| 1g | ▶| | pin 5 | pin 4 | ~0.3–0.7 V (protection diode) | 0.487 V |
| 1h | ▶| | pin 4 | pin 5 | OL or slowly rising | slowly rising |

## 2. Motor driver (ESCON 70/10), every connector unplugged (J1, J2, J3, J5, J6, USB)
| # | Mode | Red | Black | Expected (healthy) | Result |
|---|---|---|---|---|---|
| 2a1 | Ω | J1 + | J1 − | rising, not ~0 | rising |
| 2a2 | Ω | J1 − | J1 + | a value or rising, not ~0 | 20 kΩ |
| 2b1 | ▶| | J2 pin 1 | J1 + | ~0.3–0.7 V | 0.496 V |
| 2b2 | ▶| | J1 + | J2 pin 1 | OL | OL |
| 2b3 | ▶| | J1 − | J2 pin 1 | ~0.3–0.7 V | |
| 2b4 | ▶| | J2 pin 1 | J1 − | OL | |
| 2b5 | ▶| | J2 pin 2 | J1 + | ~0.3–0.7 V | |
| 2b6 | ▶| | J1 + | J2 pin 2 | OL | |
| 2b7 | ▶| | J1 − | J2 pin 2 | ~0.3–0.7 V | |
| 2b8 | ▶| | J2 pin 2 | J1 − | OL | |
| 2b9 | ▶| | J2 pin 3 | J1 + | ~0.3–0.7 V | |
| 2b10 | ▶| | J1 + | J2 pin 3 | OL | |
| 2b11 | ▶| | J1 − | J2 pin 3 | ~0.3–0.7 V | |
| 2b12 | ▶| | J2 pin 3 | J1 − | OL | |
Faulty: ~0 in both directions on any pair = shorted power stage.

## 3. Motor (maxon EC 90 flat 500267), on its own cable, ESCON unplugged
| # | Mode | Red | Black | Expected (healthy) | Result |
|---|---|---|---|---|---|
| 3a | Ω | red winding wire | brown | ~0.8–1 Ω (datasheet 0.844 Ω + cable) | |
| 3b | Ω | brown | white | ~0.8–1 Ω | |
| 3c | Ω | white | red | ~0.8–1 Ω | |
| 3d | Ω | red winding wire | motor metal body | OL | |
Subtract reading 0a from 3a–3c.

## 4. Old 48 V supply (Mean Well RSP-2000-48), **mains plug out**, output wires off
| # | Mode | Red | Black | Expected (healthy) | Result |
|---|---|---|---|---|---|
| 4a | Ω | +V out | −V out | rising, not ~0 | passed |
| 4b | Ω | +V out | ⏚ | OL | passed |
| 4c | Ω | −V out | ⏚ | OL (or very high) | passed |
| 4d | look | burn marks, bulged parts, smell, blown fuse visible through the vents | | none | **white residue coming out of the case** (likely capacitor electrolyte) |
Do not open the supply and do not touch its mains terminals.

## 5. Brake chopper powered from a 24 V supply (Mean Well RS-15-24, current-limited by its short-circuit protection)
Source: `docs/reference/maxon-235811-dsr-70-30-operating-instructions.pdf` (supply 12–70 V, no-load 15 mA, 8800 µF inside,
threshold Vth = 75 V − (sum of DIP switches ON: S1=1, S2=2, S3=4, S4=8, S5=16, S6=32) × 1 V, yellow LED = shunt active, red LED = over-temperature).
Wiring: 24 V + → pin 4, 24 V − → pin 5, nothing else. Pins 6/7 (output 1) are in parallel with the input.
| # | Check | Expected (healthy) | Result |
|---|---|---|---|
| 5a | DIP switches S1–S6 (before power): write ON/OFF, compute Vth | Vth above 48 V (e.g. 53 V) | **all OFF → Vth = 75 V** (photo IMG_9788). The 3 working towers: S3 + S5 ON → **55 V** (IMG_9784/9785/9787). ON = lever toward the "ON" print (right), away from the numbers |
| 5b | Pins 4–5 (DC V) after switch-on | ~24 V (may take ~1 s: the supply charges 8800 µF) | 24 V |
| 5c | Pins 6–7 (DC V) | same as 5b | 24 V |
| 5d | Yellow LED (shunt active) / red LED (over-temperature) | both off | both off |
| 5e | Housing after 5 min, sound, smell | cool, silent, no smell | passed |
| 5f | After switch-off: pins 4–5 before touching the wires | wait until < 1 V (the capacitors hold charge) | |
Faulty: 5b well below 24 V or the supply clicking on/off (short), or yellow LED on with Vth > 24 V.

**DIP finding (2026-10-06).** Vth 75 V is above the ESCON 70/10 supply maximum (70 V) and above the RSP-2000-48 over-voltage protection (57.6–67.2 V, `docs/reference/meanwell-rsp-2000-spec.pdf`; it shuts the output down, "re-power on to recover").
With 75 V the chopper never clamps braking energy below those limits; with 55 V (working towers) it does. Plausible cause of the failure (bus pumped up when the motor brakes), not proven: the DIP could also have been changed after the failure. Neither the Stanford guide nor the thesis/manual states a threshold.
**Set to 55 V (S3 and S5 ON) on 2026-10-06**, like the other towers. Then 5b–5f at 24 V.

## Result
| Part | Verdict | Date |
|---|---|---|
| Brake chopper | passes all meter tests and the 24 V powered test (DIP set to 55 V like the other towers). Before reuse: 48 V with a 1 A fast fuse or a 0.1 A bench supply | 2026-10-06 |
| ESCON 70/10 | power input and phase 1 upper OK; 2b3–2b12 still to do | 2026-10-05 |
| Motor | | |
| Old 48 V supply | **faulty**: 4a–4c passed but white residue leaking from the case → scrap (e-waste), replace | 2026-10-05 |

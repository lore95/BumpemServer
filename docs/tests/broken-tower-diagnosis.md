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

## Result
| Part | Verdict | Date |
|---|---|---|
| Brake chopper | passes all meter tests; current-limited bench test (0.1 A) still due before reuse | 2026-10-05 |
| ESCON 70/10 | power input and phase 1 upper OK; 2b3–2b12 still to do | 2026-10-05 |
| Motor | | |
| Old 48 V supply | **faulty**: 4a–4c passed but white residue leaking from the case → scrap (e-waste), replace | 2026-10-05 |

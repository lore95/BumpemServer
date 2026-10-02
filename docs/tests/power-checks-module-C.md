# Electrical checks before first power-on: Bump'em module C

Self-contained test specification. It can be read without any other document.

## Context
- System: Bump'em cable-perturbation device. Module C ("right" module) consists of:
  - PSU = Mean Well RSP-2000-48 switching power supply. Output 48 V DC, up to 42 A. Screw terminals labelled −V, +V, ⏚ (protective earth), L, N (230 V mains). Small 12-pin control connector CN501 (Hirose DF11-12DP). No power switch: it is on whenever its mains plug is live.
  - SHUNT = maxon Shunt Regulator 235811 (DSR 70/30). Green 10-way screw terminal block. Pins: 1–2 external resistor (unused), 3 ground safety earth, 4 +Vcc input, 5 Power Gnd input, 6 +Vcc output 1, 7 Power Gnd output 1, 8 ground safety earth, 9–10 output 2 (unused). Internal 6-way DIP switch sets its dump threshold: Vth = 75 V − (sum of ON switches, where switch n = 2^(n−1) V).
  - ESCON = maxon ESCON 70/10 motor driver. Power connector J1 (+ / −). USB socket J7.
  - E-STOP = emergency-stop button with one contact block (2 wires).
- Intended wiring:
  - PSU −V → SHUNT pin 5
  - PSU +V → SHUNT pin 4
  - PSU ⏚ → SHUNT pin 3 (PSU ⏚ also carries the mains earth wire)
  - SHUNT pin 6 → ESCON J1 +
  - SHUNT pin 7 → ESCON J1 −
  - E-STOP contact → PSU CN501 pin 7 (Remote ON-OFF) and pin 11 (+5V-AUX). Datasheet: short between pin 7 and 11 = PSU output OFF; open = ON. Required contact type: normally open (NO).
- Current state: all wiring done, PSU mains plug NOT connected. Motor-enable wire from the controller is disconnected, so the motor cannot move.

## Safety rules (apply to every test)
1. Continuity tests (T0–T4) only with the PSU mains plug disconnected.
2. Voltage tests (T6–T7) with power on: touch only with probe tips, never with fingers; never touch L / N.
3. Meter probes: black in COM, red in VΩ. Never use the A / mA / 10A sockets.
4. Meter modes: continuity = ))) symbol (beep); DC voltage = V⎓ (V with straight + dashed line), range ≥ 200 V for 48 V and ≥ 20 V for 5 V / 3.3 V.
5. Any FAIL → stop, do not power on, report the reading.

## T0: residual voltage (meter: DC volts)
- Measure PSU +V to PSU −V.
- PASS: about 0 V. FAIL: > 1 V → wait for capacitors to discharge and repeat.

## T1: meter self-test (meter: continuity)
- Touch probes together. PASS: beep, about 0 Ω.

## T2: short between + and − (meter: continuity)
- PSU +V to PSU −V.
- PASS: no beep, OR a short chirp that stops / a resistance that rises or settles in the kΩ range (capacitors charging).
- FAIL: steady beep, about 0 Ω → short circuit. Do not power on.

## T3: wiring and polarity (meter: continuity)
| # | Probe 1 | Probe 2 | PASS |
|---|---|---|---|
| T3.1 | PSU +V | SHUNT pin 4 | beep |
| T3.2 | PSU +V | SHUNT pin 5 | NO beep (beep = polarity swapped) |
| T3.3 | PSU −V | SHUNT pin 5 | beep |
| T3.4 | PSU ⏚ | SHUNT pin 3 | beep |
| T3.5 | SHUNT pin 6 | ESCON J1 + | beep |
| T3.6 | SHUNT pin 7 | ESCON J1 − | beep |

## T4: earth isolation (meter: continuity)
| # | Probe 1 | Probe 2 | PASS |
|---|---|---|---|
| T4.1 | PSU +V | PSU ⏚ | no steady beep |
| T4.2 | PSU −V | PSU ⏚ | record result only (PSU output is isolated from earth per datasheet; unknown whether SHUNT ties Power Gnd to safety earth internally) |

## T5: e-stop contact type (meter: continuity, across the two e-stop wires, e-stop disconnected from CN501 or PSU unplugged)
- Button released: PASS = no beep. Button pressed: PASS = beep. → contact is NO (correct).
- Reversed behaviour = NC contact → FAIL: replace the contact block with an NO type.

## T6: shunt threshold (visual)
- Read the SHUNT's internal DIP switch (not the example drawings on its label). Compute Vth = 75 − Σ 2^(n−1) over ON switches n.
- PASS: Vth clearly above 48 V and below 70 V (reference build: switches 3 and 5 ON → 55 V).
- FAIL: Vth ≤ 50 V → the shunt would dissipate continuously and overheat.

## T7: first power-on (only if T2, T3, T5, T6 pass)
Setup: PSU plugged into a switched power strip, strip switch OFF. Socket not shared with other experiments. Location of the room's breaker panel known. Optional: ESCON USB (J7) connected to a PC before power-on (never plug USB into a powered ESCON).
1. Switch strip ON. Observe 30 s without touching:
   - PASS: SHUNT LED "Power Dissipation Active" stays OFF; SHUNT LED "Overtemperature" OFF; ESCON status LED lights; PSU fan may run.
   - FAIL: dissipation LED ON, smoke, smell, buzzing, breaker trips → switch OFF.
2. Meter DC volts, SHUNT pin 4 (red) to pin 5 (black): PASS = 47–49 V (PSU adjustable 42–56 V).
3. E-stop (if wired): press → ESCON LED goes off (PSU output off); release → back on. PASS = both.
4. Optional, PSU on: CN501 pin 11 to pins 8–10 = about +5 V (identifies pin 11).
5. Switch strip OFF. Wait 1 min before touching wiring.

## Report format
T0 … T7 each: PASS / FAIL + reading (e.g. "T2 PASS, chirp then open"; "T4.2: beep 0.3 Ω"; "T6: switches 3,5 ON → 55 V").

# Preliminary open-loop test: Teensy drives module C (no force sensor)

Goal: check that the Mac → USB → Teensy → DAC → ESCON → motor chain works, before the amplifier is connected.
The Teensy runs **open-loop** (PD gains 0): target force → feedforward current → DAC → ESCON. The force reading is ignored.
Nothing measures the real force, so forces stay small.

## Why these settings
Confirmed values: ESCON set value **10 V = 30 A** (`escon/moduleA_left_2026-10-01.edc`), motor torque constant **0.231 Nm/A** (maxon 500267), drum radius 0.01905 m.
Firmware feedforward: `ides = kff · F · rc / kt` with firmware `kt = 0.1524`, DAC full scale = `i_full` = 30 at 3.3 V.
Real force / target = kff · (3.3 V / 30) · (3 A/V) · (0.231 / 0.1524) ≈ **0.5 · kff**. Default `kff = 7.5` → about **3.75× the target**; **`kff = 2` → about 1× the target**. Calculated, not measured; friction makes the real pull lower.

| Setting | Value | Reason |
|---|---|---|
| `kp_track` `kd_track` `kp_pulse` `kd_pulse` | 0 | open-loop |
| `kff` | 2 | target ≈ real pull |
| `baseline_n` | 2 | gentle hold |
| `fmax_n` | 30 | firmware refuses targets above 30 N |
| `ch_A` `ch_B` | 0 | only C (D is off by default) |

Settings live in Teensy RAM: unplugging the Teensy's USB restores the closed-loop defaults.

## Wiring (Teensy USB out, 48 V off; right-side blue − rail as ground)
Actual layout (2026-10-02, T = Teensy, D = DAC): **− rail** T G, D GND · **+ rail** T 3V, D VCC (3.3 V only) · T 19 → D SCL (purple wire) · T 18 → D SDA (white wire). ⚠️ SDA wire and module C ground are both white: label them (or make SDA grey). Colours per `knowledge/wiring.md` → Recabling plan. Check + rail ↔ − rail does NOT beep. Loopback wires to 14–17 removed (2026-10-02).

| # | From | To |
|---|---|---|
| 1 | T G (right-edge top G row, free hole) | blue − rail (right side) |
| 2 | white (module C ground, after recabling) | blue − rail |
| 3 | green (SP−) | blue − rail |
| 4 | short wire from T 16 row | blue − rail (force input reads 0) |
| 5 | yellow (enable) | T 29 row (left edge, a/b) |
| 6 | blue (SP+, female end) | D VC pin |
| — | red + rail | nothing |
| — | brown (force), pink, black (spares) | not plugged, ends taped |

Checks: rail continuity between all four rail holes (rails can be split mid-board) · T 3V ↔ − rail must NOT beep · nothing in the 5V row, the + rail, or rows 14, 15, 17.
ESCON: J1 power, J2 motor, J3 Hall (blue on pin 5) as fixed on 2026-10-01.

Script: `scripts/open_loop_test.sh` (C), `… A` (A) or `… AC` (both, same pulse at the same time) runs Setup, Dry run and Run below with prompts for the 48 V. Pulse duration 400 ms (shortened from 600 on 2026-10-02). AC only after A and C each passed alone; switch the two 48 V supplies on one at a time, separate sockets.

## Setup
Rope tied to a fixed anchor · no person · treadmill off · everyone clear · **hand on the 48 V strip switch** (e-stop not wired yet).

```sh
conda activate BumpemHome
P=/dev/cu.usbmodem169222501
bumpem info --port $P                      # expect proto=1, fw=1.0.0
for k in kp_track kd_track kp_pulse kd_pulse; do bumpem set $k 0 --port $P; done
bumpem set kff 2 --port $P
bumpem set baseline_n 2 --port $P
bumpem set fmax_n 30 --port $P
bumpem set ch_A 0 --port $P
bumpem set ch_B 0 --port $P
bumpem get --port $P                       # check the values above
```

## Dry run (48 V off)
`bumpem arm --port $P --watch 3` → C target 2.0 · `bumpem pulse C=20 --rise 50 --dur 400 --fall 50 --port $P --watch 2` → 2 → 22 → 2 · `bumpem release --port $P`.

## Run
| # | Action | Expect | Stop if |
|---|---|---|---|
| 1 | 48 V strip **on** | ESCON LED green **blinking** (disabled) | red LED |
| 2 | `bumpem arm --port $P --watch 3` | LED **steady green** (enabled); rope tightens gently over 2 s | hard pull, motor spins |
| 3 | `bumpem pulse C=5 --rise 50 --dur 400 --fall 50 --port $P --watch 2` | small tug; telemetry: C target 2 → 7 N, DAC C rises | drum pays out instead of pulling |
| 4 | same with `C=10` | bigger tug | |
| 5 | same with `C=20` | clear tug (~22 N target) | |
| 6 | `bumpem release --port $P` | rope slackens over 1 s; LED back to blinking | |
| 7 | 48 V strip **off** | | |

Emergency: strip switch off, or `bumpem estop --port $P` from a second terminal.

## Report
For each step: what the LED did and what the rope did (gentle / tug / nothing / wrong direction). The CLI telemetry shows target and measured only (measured C ≈ 0 because pin 16 is grounded).
Expected DAC codes (not shown by the CLI): baseline 68, C=5 → 238, C=10 → 409, C=20 → 750 (≈ 0.05–0.6 V on VC).

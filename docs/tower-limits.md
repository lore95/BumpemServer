# Tower limits

Measured 2026-11-20 on the Mac, ropes on a fixed (slightly wobbly) anchor, nobody attached. Valid until the steel shafts are in (`TODO.md` → 4 · Hardware finish). PDF: `scripts/todo_pdf.sh docs/tower-limits.md docs/tower-limits.pdf "Tower limits"`.

## Use in studies now

| | Limit |
|---|---|
| **Board cap** | **75 N** pull (Max force 79 N = 75 + 4 N rest): the board refuses more (D56) |
| **Pull amplitude (A, B, D)** | **≤ 50 N** above the 4 N rest tension: above it the pages warn that the force may not be reached |
| **Pull amplitude (C)** | **≤ 20 N** (50 N not tested yet on the 20 A range) |
| Diagonal pulls | split over two towers (45°: 50 N → 35 N each): same limits per tower |
| Marker lines | check on all four towers before and after every session; a broken line = stop, lower the limit |

Why 50 N and not 100 N: creep and slip start between 75 and 120 N depending on the tower, every slipping pull wears the aluminium shaft further (D got worse after one), and the joint has to carry the start peak (50 N pulls peaked at 63–72 N on the anchor), not the average.

## Settings these numbers hold for

| | Value |
|---|---|
| ESCON set value (all four) | 0 V → 0 A, 3.3 V → **20 A** (`escon/module*_2026-11-20_20A.edc`, D55) |
| Board | `i_full` 20, **kff 0.9**, kp 0.08, **kd 0.2** (track and pulse), rest 4 N, max 79 N since D56 (196 N during these tests), fault 200 N |
| Pull | 50 ms ramp up, 500 ms hold, 50 ms ramp down; force = rope load cell |

## Per tower

Target = pull + 4 N rest. Hold = average over the hold; range = lowest–highest during the pull (start peak included).

| Tower | Pull | Hold (target) | Range | Max current | Result |
|---|---|---|---|---|---|
| **A** (left) | 20 N | 23.3 N (24) | 17.6–29.5 N | 3.3 A | ✅ |
| | 50 N | 53.6 N (54) | 42–72 N | 7.7 A | ✅ start overshoot (anchor) |
| | 100 N | 100.4 N (104) | 82–144 N | 14.3 A | ✅ once; above 100 N not tested |
| **B** (front) | 20 N | 23.3 N (24) | 14.5–36.9 N | 4.5 A | ✅ start swing (anchor) |
| | 50 N | 51.0 N (54) | 46–63 N | 8.1 A | ✅ |
| | 100 N | 103.2 N (104) | 91–131 N | 14.3 A | ✅ slight fade over the hold |
| | 120 N | 113.5 N (124) | 92–157 N | 19.9 A | ⚠️ **creep**: 114 → 92 N while the current rises |
| **C** (right) | 20 N | 22.8 N (24) | 18.8–28.9 N | 3.5 A | ⚠️ flips 17 ↔ 27 N every 10 ms (C only) |
| | 75 N | 57.7 N (79) | 46–73 N | 12.7 A | ❌ **slip**, marker line broken |
| **D** (back) | 20 N | 21.6 N (24) | 18–26 N | 3.7 A | ✅ |
| | 50 N | 51.1 N (54) | 43–67 N | 7.5 A | ✅ |
| | 100 N | 80.2 N (104) | 39–116 N | 18.3 A | ❌ **stick-slip** (110 → 39 N in 10 ms) |
| | 100 N, after tightening | 54.4 N (104) | 35–82 N | 19 A | ❌ worse: still slipping |

Rope force per amp (a healthy joint): A ≈ 7, B ≈ 6.3–9, D ≈ 7 N/A; C ≈ 5.5 N/A (slipping). A tower that needs much more current for the same force is slipping.

## Creep and slip

| | Creep | Slip |
|---|---|---|
| What | drum turns slowly on the shaft | the joint lets go |
| Force | fades during the hold, current rises | drops suddenly, often catches again (stick-slip) |
| Marker line | barely offset | clearly broken |

Cause on all towers: the clamp collar on a soft **aluminium** drive shaft. At 100 N the joint carries ≈ 1.9 N·m (100 N × 19 mm drum radius); the motor can put ≈ 4.4 N·m on it at 20 A. Stanford specifies a "3/8in x 3in Linear Shaft" (hardened steel).

## What lifts the limits

1. Steel shafts on all four towers (TODO 🔴, order and fitting steps there).
2. Then on a **solid** anchor: marker check after 50 / 100 / 150 N, no fade over the hold, start overshoot measured without the anchor's give.
3. Then new limits here.

Raw data: `Logs/force_20261120_13*_20A_*.csv`, `Logs/force_20261120_14*_20A_*.csv`; notes in `STATUS.md` (2026-11-20).

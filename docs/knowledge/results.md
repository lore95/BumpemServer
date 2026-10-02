# Reference performance (regression targets)

Source: thesis Tables 2–5. Use these to check that a refactor did not degrade behavior.

Rise time = time to 80 % of target. Peak = max in impulse window.

| Dir | Module | 100 N peak | 100 N rise (ms) | 150 N peak | 150 N rise (ms) |
|---|---|---|---|---|---|
| left | 1 (A) | 91.6 ± 0.6 | 30.0 ± 3.6 | 135.5 ± 5.5 | 32.5 ± 5.0 |
| front | 2 (B) | 100.6 ± 4.5 | 34.0 ± 5.5 | 140.6 ± 0.9 | 30.0 ± 0.7 |
| right | 3 (C) | 114.9 ± 5.5 | 34.0 ± 8.9 | 127.4 ± 2.7 | 45.0 ± 5.8 |
| front-left | 1+2 | 81.7 ± 4.1 | 40.0 ± 8.2 | 123.5 ± 2.6 | 40.0 ± 10.0 |
| front-right | 2+3 | 94.8 ± 6.5 | 42.0 ± 4.5 | 131.6 ± 2.6 | 37.5 ± 5.0 |

Overall at 100 N: peak 96.7 ± 12.3 N, rise 36.0 ± 4.9 ms.
Baseline tracking: 5 N and 10 N stable, no drift (§5.1).

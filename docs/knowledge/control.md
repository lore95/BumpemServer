# Force control (as implemented)

Source of truth: `legacy/Arduino_Script.ino`. Thesis §2.6 and Appendix pseudocode match structurally.

## Parameters
| Name | Value | Line |
|---|---|---|
| Loop period `T` | 10 ms (`delay(T)`, not fixed-rate) | 22, 224 |
| `Pgain` | 0.24 | 25 |
| `Dgain` | 3.5 | 26 |
| `feedforwardGain` | 7.5 | 29 |
| `rc` (drum radius) | 0.01905 m | 32 |
| `kt` | 0.1524 | 33 |
| Baseline | 5.0 N | 36 |
| Impulse force | 100 N | 77 |
| Impulse duration | **600 ms** (thesis §4.3 says 300 ms) | 78 |
| Impulse ramp | 50 ms linear from baseline | 335 |
| Diagonal scale | 0.7071 per module | 83 |
| Startup ramp | 0 → baseline over 2000 ms | setup() |

## Law (per module, every loop)
```
f      = raw/1023 * 200                 # N
ef     = fdes - f
d      = (f - f_prev) / T               # T in ms → N/ms (Dgain is tuned for this unit)
ipd    = Pgain*ef - Dgain*d
iffwd  = feedforwardGain * fdes * rc/kt
ides   = ipd + iffwd
U      = clamp(ides * 3.3/30, 0, 3.3)   # V to DAC; implies 3.3 V ↔ 30 (ESCON AnIn2 scaling — verify in escon/)
DAC    = int(4095/3.3 * U)
```

## Derived observation (verify on hardware)
Feedforward alone reaches DAC full scale (`ides = 30`) at `fdes = 30*kt/(7.5*rc) ≈ 32 N`.
So at 100 N the command is **saturated** for the whole impulse. Peak force is then set by the ESCON
current limit / AnIn2 scaling and the mechanics, not by the PD loop. This is consistent with the
module-to-module peak differences in the thesis (Table 2: 81.7–114.9 N).

## Behavioral facts relevant to the host
- Impulses are **blocking** (`while` loop, 600 ms). Serial commands are not read during an impulse.
- Telemetry is printed every loop for all 4 modules (see `docs/PROTOCOL.md`).
- Module D is driven to baseline even though it is out of service.

## ESCON setpoint scaling (added 2026-09-30)
The Stanford ESCON configuration that manual §4.3.1 says to load (`escon/stanford/`, decoded in `escon/README.md`) maps AnIN2 **0–10 V → 0–30 A (3 A/V)**.
The firmware's `U = ides * 3.3/30` assumes **3.3 V → 30 A**. If the IBMS drivers use the Stanford file, the DAC's full scale 3.3 V commands **9.9 A**.
Consistency check (not proof): 9.9 A × kt / rc gives 79 N with the firmware's kt = 0.1524, or 118 N with the config's 226.8 mNm/A, which brackets the thesis 100 N peaks (81.7–114.9 N, `results.md`).
So peak force may be set by this 9.9 A ceiling. Confirm by reading each driver's configuration with ESCON Studio before changing `i_full` or `kff`.
**Confirmed 2026-10-01 on module A's driver** (`escon/moduleA_left_2026-10-01.edc`): set value 0–10 V → 0–30 A. So the current at DAC full scale (3.3 V) is **9.9 A**: firmware `i_full` should be **9.9**, not 30 (or the ESCON scaling changed instead). Decide after the first test; changing it raises the commanded current about 3× for the same force target.

# Load cell calibration

Source: thesis §3.2, Table 1.

Method: known masses 6/8/12 kg (58.86/78.48/117.72 N). IAA100 zero/span trimmed so 0–3.3 V ↔ 0–200 N.
Firmware uses one linear map for all modules: `f = raw/1023*200` (`.ino:233`). No per-sensor coefficients in code.

| Target (N) | S1 | S2 | S3 | S4 |
|---|---|---|---|---|
| 0 | 0.39 | 0.29 | 0.37 | 0.10 |
| 58.86 | 57.67 | 56.36 | 56.11 | 57.36 |
| 78.48 | 77.03 | 78.59 | 76.25 | 77.31 |
| 117.72 | 117.50 | 119.65 | 117.30 | 118.47 |

Mean error ≈ 1.7 %, max < 2.5 %.

Unknown: sensor N ↔ module letter mapping. Assumed S1=A … S4=D. Verify.
Resolution: 200 N / 1023 ≈ 0.2 N per ADC count.

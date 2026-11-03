# Sensor calibrations
Weight calibrations from BumpemUI `calibrate.html` (DECISIONS D42, D43). `apply_calibration.bat` on the lab PC uses the
newest `calibration_*.csv` here (or in BumpemLab / Downloads) and writes the gains into `settings.json`.

| File | Setup | Gains (D43 fit) | Notes |
|---|---|---|---|
| `calibration_20261103_1413.csv` | Mac + Teensy fw 1.0.1, weights 12 / 16 / 32 kg hung on each sensor, sensors on their own amplifiers (B 200 kg, A/C/D 100 kg) | A 1.013, B 2.075, C 0.953, D 0.998 | Row A 14:06:19 relabelled 16 → 32 kg (user: mislabelled; it reads full scale and is left out either way). 32 kg saturates A, C, D (200 N raw) |

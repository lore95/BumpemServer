# Printed tower parts (CadQuery)

Parts that bolt to the tower profile (90x90 light B-type, slot 10, `docs/knowledge/hardware.md`) with the existing M6 button-head screws and slot-10 T-nuts.
All mounting dimensions live in `tower.py`; device sizes come from the datasheets in `docs/reference/` (Futek IAA100 FI1573, Mean Well RS-15 case 971A).
Overview with renders: `out/parts-overview.pdf`.

| File | Part | Status |
|---|---|---|
| `out/test_fit.stl` | 3 test plates, slot key clearance 0.1 / 0.2 / 0.3 mm per side (1 / 2 / 3 notches) | print first |
| `out/iaa100_din_mount.stl` | printed 35 mm DIN rail for the Futek IAA100's spring clip | ready (from datasheet) |
| `out/rs15_plate.stl` | plate for the Mean Well RS-15-24, 2 × M3 × 6 from the back | ready (from datasheet) |
| `parts.py` | concepts: signal connector plate, cable clip, power-strip hooks | sizes missing |

Build: `pip install cadquery matplotlib`, then in this folder `python test_fit.py`, `python make_stl.py`, `python overview.py`.
Print PETG or ASA, no supports; the two holders stand on their end (brim recommended).
After the test print: set `KEY_CLEAR` in `tower.py` to the plate that slid in without play, then re-run `make_stl.py`.
Not printed: the 48 V supply RSP-2000-48 (295 × 127 × 41 mm, 1.95 kg, needs airflow) needs metal brackets.

# Printed tower parts (CadQuery)

Parts that bolt to the tower profile (90x90 light B-type, slot 10, `docs/knowledge/hardware.md`) with the existing M6 button-head screws and slot-10 T-nuts.
All mounting dimensions live in `tower.py`; device sizes come from the datasheets in `docs/reference/` (Futek IAA100 FI1573, Mean Well RS-15 case 971A).
Overview with renders: `out/parts-overview.pdf`.

| File | Part | Status |
|---|---|---|
| `out/fit_check.stl` + `out/fit_check.pdf` | **one of each** (test plate 0.2 mm, IAA100 mount, RS-15 plate, 48 V bracket A) on one bed, 157 × 51 mm, 107 mm high | print first |
| `out/test_fit.stl` | 3 test plates, slot key clearance 0.1 / 0.2 / 0.3 mm per side (1 / 2 / 3 notches) | if 0.2 does not fit |
| `out/iaa100_din_mount.stl` | printed 35 mm DIN rail for the Futek IAA100's spring clip | ready (from datasheet) |
| `out/rsp2000_brackets.stl` | 2 end brackets for the Mean Well RSP-2000-48 (case 952D): A 2 × M4, B 1 × M4 (M4 × 12 from the back), 10 mm air gap | ready (from datasheet) |
| `out/rs15_plate.stl` | plate for the Mean Well RS-15-24, 2 × M3 × 6 from the back | ready (from datasheet) |
| `parts.py` | concepts: signal connector plate, cable clip, power-strip hooks | sizes missing |

Build: `pip install cadquery matplotlib`, then in this folder `python test_fit.py`, `python make_stl.py`, `python fit_check.py`, `python overview.py`.
Print PETG or ASA, no supports; the two holders stand on their end (brim recommended).
After the test print: set `KEY_CLEAR` in `tower.py` to the plate that slid in without play, then re-run `make_stl.py`.
48 V supply (1.95 kg, warm): print its brackets in ASA, or PETG at 40 %+ infill; keep the fan ends free.

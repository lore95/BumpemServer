# Printed tower parts (CadQuery)

Parts that bolt to the tower profile (90x90 light B-type, slot 10, `docs/knowledge/hardware.md`) with the existing M6 button-head screws and slot-10 T-nuts.
All mounting dimensions live in `tower.py`; device sizes come from the datasheets in `docs/reference/` (Futek IAA100 FI1573, Mean Well RS-15 case 971A).
Overview with renders: `out/parts-overview.pdf`. **Assembly guide** (what goes on which tower face, screws per tower, steps): `out/assembly-guide.pdf` (`python assembly_guide.py`, after `overview.py`).

| File | Part | Status |
|---|---|---|
| `out/fit_check.stl` + `out/fit_check.pdf` | **one of each** (test plate 0.2 mm, IAA100 mount, RS-15 plate, 48 V bracket A) on one bed, 174 × 170 mm, 18 mm high | printed 2026-10-22: key 0.2 fits, devices fit |
| `out/test_fit.stl` | 3 test plates, slot key clearance 0.1 / 0.2 / 0.3 mm per side (1 / 2 / 3 notches) | if 0.2 does not fit |
| `out/iaa100_din_mount.stl` | printed 35 mm DIN rail for the Futek IAA100's spring clip | ready (from datasheet) |
| `out/rsp2000_brackets.stl` | 2 end brackets for the Mean Well RSP-2000-48 (case 952D): A 2 × M4, B 1 × M4 (M4 × 12 from the back), 10 mm air gap | ready (from datasheet) |
| `out/rsp2000_bracket_B.stl` | bracket B alone (fan end, 1 × M4), 82 × 107 mm: 44 mm past the supply (A: 24) so the T-nuts fit (2026-10-22). `fit_check.stl` contains only A, so print this to complete one tower | ready |
| `out/all_parts.3mf` | **the whole print job in one file** (`make_stl.py`): 14 parts as separate objects (4 RS-15, 3 IAA100, 3 A, 4 B), 3 groups of 250 × 210 mm | to print |
| `out/rs15_plate.stl` | plate for the Mean Well RS-15-24, 2 × M3 × 6 from the back, 128 × 51 × 14 mm (M6 holes moved out 2026-10-22) | ready, reprint |
| `parts.py` | concepts: signal connector plate, cable clip, power-strip hooks | sizes missing |

**Print job for the makerspace:** `./druckauftrag.sh` → `out/bumpem-druckauftrag-2026-10-22.zip` (handoff PDF in German from `druckauftrag-2026-10-22.tex`: fit-check result, changes, what to print, settings + `assembly-guide.pdf` + `all_parts.3mf`). New job: copy the `.tex` with a new date.
Build: `pip install cadquery matplotlib`, then in this folder `python test_fit.py`, `python make_stl.py`, `python fit_check.py`, `python overview.py`.
Print PETG or ASA, **flat, key side down** as exported. Supports touching the build plate under the plate wings (2.5 mm high, the face against the profile: rough is fine), under the 48 V brackets' pad ledges (10.5 mm beyond the plate, 7.5 mm high) and under the DIN rail's 5 mm flanges (the IAA100 clip hooks there: keep them straight). Screw-head pockets on the bottom (Ø 6–8 mm) bridge without support.
PETG (check 2026-10-22, `assembly-guide.pdf` p. 2): support Z gap 0.2–0.25 mm, 4 walls, ≥ 40 % infill, glue stick on smooth PEI. Loads are tiny (48 V bracket: 9.6 N shear each, ~2 N pull-off); the limits are heat (PETG softens ~70 °C; not PLA for the 48 V brackets) and M6 clamping (tighten ~2 N·m: 2 kN under the button head ≈ 38 MPa, near PETG's ~55 MPa yield). The first version stood the holders on their end (up to 107 mm tall): it toppled halfway on the makerspace printer, 4 attempts (2026-10-19).
Do not change (they set the fit): key 9.6 × 2.5 mm, 5 mm plate under the M6 heads, M6 / M3 / M4 hole positions, DIN rail 35 × 7.5 mm with 1 mm flanges, 10 mm pad on the 48 V brackets. Extra material elsewhere is fine.
After the test print: set `KEY_CLEAR` in `tower.py` to the plate that slid in without play, then re-run `make_stl.py`.
48 V supply (1.95 kg, warm): print its brackets in ASA, or PETG at 40 %+ infill; keep the fan ends free.

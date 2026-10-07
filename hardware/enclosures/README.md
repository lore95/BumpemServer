# Printed tower parts (CadQuery)

Parts that bolt to the tower profile (90x90 light B-type, slot 10, `docs/knowledge/hardware.md`) with the existing M6 button-head screws and slot-10 T-nuts.
All mounting dimensions live in `tower.py`.

| File | Part | Status |
|---|---|---|
| `test_fit.py` → `out/test_fit.stl` | 3 test plates, slot key clearance 0.1 / 0.2 / 0.3 mm per side (1 / 2 / 3 notches) | to print |

Build: `pip install cadquery`, then `python test_fit.py` in this folder. Print PETG or ASA, flat side down as exported, no supports.
After the test: set `KEY_CLEAR` in `tower.py` to the plate that slid in without play.

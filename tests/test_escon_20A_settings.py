"""scripts/escon_20A_settings.py: saved control values for the ESCON 20 A range, run by update.bat."""
import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "escon_20A_settings.py"
OLD = {"kp_track": 0.24, "kd_track": 3.5, "kp_pulse": 0.24, "kd_pulse": 3.5, "kff": 5.5, "i_full": 30.0,
       "gain_B": 2.12, "offset_A": -3.5, "fmax_n": 196.0}


def _run(settings: Path, *extra: str) -> str:
    return subprocess.run([sys.executable, str(SCRIPT), "--settings", str(settings), *extra],
                          capture_output=True, text=True, check=True).stdout


def test_old_range_gets_the_20A_values_and_keeps_the_rest(tmp_path):
    f = tmp_path / "settings.json"
    f.write_text(json.dumps({"saved": "2026-11-12T10:00:00", "params": OLD}))
    out = _run(f)
    p = json.loads(f.read_text())["params"]
    assert {k: p[k] for k in ("i_full", "kff", "kp_track", "kp_pulse", "kd_track", "kd_pulse")} == \
        {"i_full": 20.0, "kff": 0.9, "kp_track": 0.08, "kp_pulse": 0.08, "kd_track": 0.2, "kd_pulse": 0.2}
    assert (p["gain_B"], p["offset_A"], p["fmax_n"]) == (2.12, -3.5, 79.0)
    assert json.loads((tmp_path / "settings.json.bak").read_text())["params"] == OLD
    assert "kff: 5.5 -> 0.9" in out


def test_already_20A_is_left_alone(tmp_path):
    f = tmp_path / "settings.json"
    tuned = dict(OLD, i_full=20.0, kff=1.0)                      # tuned later on that PC
    f.write_text(json.dumps({"saved": "x", "params": tuned}))
    assert "nothing changed" in _run(f)
    assert json.loads(f.read_text())["params"] == tuned and not (tmp_path / "settings.json.bak").exists()


def test_no_file_and_dry_run(tmp_path):
    f = tmp_path / "settings.json"
    assert "firmware default -> 0.9" in _run(f, "--dry-run") and not f.exists()
    _run(f)
    assert json.loads(f.read_text())["params"]["i_full"] == 20.0

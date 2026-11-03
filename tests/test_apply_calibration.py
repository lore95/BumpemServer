"""scripts/apply_calibration.py: gains from a calibrate-page CSV into settings.json (D42)."""
import csv
import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "apply_calibration.py"
HEAD = ["time", "sensor", "kind", "mass_kg", "expected_n", "raw_mean_n", "raw_sd_n", "samples", "clipped_pct", "tare_n",
        "net_n", "board_gain", "board_offset", "f_full", "g", "fw", "port"]


def _csv(path: Path, sensors: dict[str, tuple[float, float, list[float]]]) -> Path:
    """sensors: {X: (true gain, tare raw N, masses kg)} → rows as the page writes them (raw = force / gain + tare)."""
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(HEAD)
        for c, (gain, tare, masses) in sensors.items():
            w.writerow(["t", c, "tare", 0, 0, tare, 0.3, 200, 0, tare, 0, 1, 0, 200, 9.81, "1.0.1", "x"])
            for m in masses:
                raw = m * 9.81 / gain + tare
                w.writerow(["t", c, "point", m, m * 9.81, raw, 0.3, 200, 0, tare, raw - tare, 1, 0, 200, 9.81, "1.0.1", "x"])
    return path


def _run(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], capture_output=True, text=True)


def test_gains_written_offsets_scaled(tmp_path):
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"saved": "x", "params": {"kff": 2, "gain_B": 2.12, "offset_B": -4.24, "offset_A": -1.0}}))
    data = _csv(tmp_path / "calibration_20261103_1300.csv",
                {"A": (1.05, 0.4, [2, 5, 8]), "B": (3.2, 1.0, [2, 5, 8]), "C": (0.98, 0.0, [5])})
    r = _run(data, "--settings", settings)
    assert r.returncode == 0, r.stderr
    p = json.loads(settings.read_text())["params"]
    assert p["kff"] == 2 and p["gain_A"] == 1.05 and p["gain_C"] == 0.98
    assert p["offset_A"] == -1.05                                   # scaled by 1.05 / 1 (no gain_A before = 1)
    assert "gain_B" in p and p["gain_B"] == 2.12                    # 3.2 is outside 0.5-3: not written
    assert "NOT written" in r.stdout and "one weight only" in r.stdout
    assert json.loads((tmp_path / "settings.json.bak").read_text())["params"]["gain_B"] == 2.12
    assert (tmp_path / "calibration_20261103_1300_applied.txt").is_file()


def test_dry_run_and_newest_file(tmp_path):
    settings = tmp_path / "settings.json"
    _csv(tmp_path / "calibration_20261103_1300.csv", {"D": (1.1, 0.2, [2, 5])})
    r = _run("--settings", settings, "--search", tmp_path, "--dry-run")
    assert r.returncode == 0 and "D: gain 1.1000" in r.stdout and not settings.exists()
    r = _run("--settings", settings, "--search", tmp_path)
    assert json.loads(settings.read_text())["params"] == {"gain_D": 1.1}


def test_no_csv(tmp_path):
    r = _run("--settings", tmp_path / "s.json", "--search", tmp_path)
    assert r.returncode != 0 and "No calibration_" in r.stderr

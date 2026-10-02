"""Angle -> module amplitudes (bumpem/geometry.py, docs/API.md)."""
import math

import pytest

from bumpem.geometry import normalize, reachable, split

ACD = {"A", "C", "D"}   # setup 2026-10-02: B (front) not installed


def test_on_axis_single_module():
    assert split(90, 20) == {"A": 20}
    assert split(-90, 20) == {"C": 20}
    assert split(180, 20) == {"D": 20}
    assert split(0, 20) == {"B": 20}


def test_diagonal_matches_legacy_scale():
    # legacy/Arduino_Script.ino:82: each of the two cables gets force * 0.7071
    amps = split(135, 100, ACD)
    assert amps == {"A": 70.71, "D": 70.71}
    assert split(-135, 100, ACD) == {"D": 70.71, "C": 70.71}


def test_general_split_is_a_vector_decomposition():
    amps = split(120, 50, ACD)                     # 30 deg past A towards D
    assert amps == {"A": round(50 * math.cos(math.radians(30)), 2), "D": round(50 * math.sin(math.radians(30)), 2)}
    assert math.hypot(amps["A"], amps["D"]) == pytest.approx(50, abs=0.01)


def test_angle_normalised():
    assert normalize(270) == -90 and normalize(-180) == 180 and normalize(450) == 90
    assert split(270, 10, ACD) == {"C": 10}


def test_needs_disabled_module():
    with pytest.raises(ValueError, match="module B"):
        split(45, 10, ACD)
    with pytest.raises(ValueError, match="> 0"):
        split(90, 0)


def test_reachable_arcs():
    assert reachable(ACD) == [{"from_deg": 90.0, "to_deg": -90.0}]
    assert reachable({"A", "B", "C", "D"}) == [{"from_deg": -180.0, "to_deg": 180.0}]
    assert reachable({"A", "C"}) == [{"from_deg": 90.0, "to_deg": 90.0}, {"from_deg": -90.0, "to_deg": -90.0}]
    assert reachable(set()) == []

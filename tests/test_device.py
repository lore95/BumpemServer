"""Board client end-to-end over the real-time simulator."""
import pytest

from bumpem.device import Board, BoardError
from bumpem.sim import SimLink


@pytest.fixture
def board():
    b = Board(SimLink(realtime=True, seed=0))
    yield b
    b.close()


def test_info_get_set(board):
    assert board.info()["proto"] == "1"
    assert board.get("kff") == {"kff": 7.5}
    board.set("kff", 1.0)
    assert board.get("kff")["kff"] == 1.0
    assert len(board.get()) == 32


def test_errors_raise(board):
    with pytest.raises(BoardError, match="not armed"):
        board.pulse(1, {"A": 50}, rise_ms=0, dur_ms=100, fall_ms=0)


def test_arm_pulse_telemetry(board):
    board.set("arm_ms", 0)
    board.arm()
    board.pulse(1, {"A": 30}, rise_ms=20, dur_ms=100, fall_ms=20)
    peak = 0.0
    for t in board.telemetry(timeout=0.5):
        peak = max(peak, t.target["A"])
        if t.t_ms > 400:
            break
    assert peak == 35.0


def test_estop_not_blocked(board):
    board.estop()
    for t in board.telemetry(timeout=0.5):
        if t.state == "ESTOP":
            break
    else:
        pytest.fail("no ESTOP telemetry")

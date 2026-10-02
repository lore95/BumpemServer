import pytest

from bumpem.protocol import Ack, Event, Info, Param, Telemetry, parse_line, pulse_cmd, set_cmd

T_LINE = "T,1234,ARMED,7,100.00,97.31,4095,5.00,5.10,1846,5.00,4.90,1846,0.00,0.00,0\r\n"


def test_parse_telemetry():
    t = parse_line(T_LINE)
    assert isinstance(t, Telemetry)
    assert (t.t_ms, t.state, t.pulse_id) == (1234, "ARMED", 7)
    assert t.target["A"] == 100.0 and t.measured["A"] == 97.31 and t.dac["A"] == 4095
    assert t.dac["D"] == 0


def test_parse_other_types():
    assert parse_line("A,OK,PULSE,7") == Ack(True, "PULSE", "7")
    assert parse_line("A,ERR,SET,out of range") == Ack(False, "SET", "out of range")
    assert parse_line("E,500,PSTART,7") == Event(500, "PSTART", ("7",))
    assert parse_line("I,proto=1,fw=1.0.0").fields == {"proto": "1", "fw": "1.0.0"}
    assert isinstance(parse_line("I,proto=1"), Info)
    assert parse_line("P,kp_track,0.24000") == Param("kp_track", 0.24)
    assert parse_line("garbage line") == "garbage line"
    assert parse_line("T,bad") == "T,bad"


def test_pulse_cmd():
    assert pulse_cmd(1, {"A": 95}, rise_ms=50, dur_ms=600, fall_ms=0) == "PULSE 1 0 50 600 0 95 0 0 0"
    assert set_cmd("kff", 1.0) == "SET kff 1"


@pytest.mark.parametrize("kw", [
    dict(rise_ms=400, dur_ms=600, fall_ms=300),   # ramps longer than duration
    dict(rise_ms=50, dur_ms=0, fall_ms=0),
    dict(rise_ms=50, dur_ms=600, fall_ms=0, delay_ms=-1),
])
def test_pulse_cmd_rejects(kw):
    with pytest.raises(ValueError):
        pulse_cmd(1, {"A": 50}, **kw)


def test_pulse_cmd_rejects_bad_amps():
    with pytest.raises(ValueError):
        pulse_cmd(1, {"E": 50}, rise_ms=0, dur_ms=100, fall_ms=0)
    with pytest.raises(ValueError):
        pulse_cmd(1, {"A": -1}, rise_ms=0, dur_ms=100, fall_ms=0)

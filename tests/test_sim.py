"""Simulator in virtual time (no sleeping): state machine, pulse shape, validation."""
from bumpem.protocol import Ack, Event, Telemetry, parse_line
from bumpem.sim import SimLink


def read(link, n):
    return [parse_line(link.readline().decode()) for _ in range(n)]


def send(link, line):
    link.write((line + "\n").encode())
    out = read(link, 20)
    return next(m for m in out if isinstance(m, Ack)), out


def armed_link(**params):
    link = SimLink(realtime=False, noise_n=0, seed=0)
    send(link, "SET arm_ms 0")
    for k, v in params.items():
        send(link, f"SET {k} {v}")
    send(link, "ARM")
    read(link, 10)
    assert link.state == "ARMED"
    return link


def test_boots_disarmed_and_rejects_pulse():
    link = SimLink(realtime=False)
    ack, _ = send(link, "PULSE 1 0 50 600 0 95 0 0 0")
    assert not ack.ok and ack.detail == "not armed"


def test_pulse_trapezoid_on_one_channel():
    link = armed_link()
    ack, first = send(link, "PULSE 3 0 50 300 100 95 0 0 0")
    assert ack.ok
    msgs = first + read(link, 60)
    tel = [m for m in msgs if isinstance(m, Telemetry)]
    peak = max(t.target["A"] for t in tel)
    assert peak == 100.0                                  # baseline 5 + amplitude 95
    assert all(t.target["B"] == 5.0 for t in tel)         # others hold baseline
    assert all(t.target["D"] == 0.0 for t in tel)         # D disabled by default
    kinds = [m.kind for m in msgs if isinstance(m, Event)]
    assert kinds.index("PSTART") < kinds.index("PEND")
    assert tel[-1].target["A"] == 5.0


def test_delay_postpones_start():
    link = armed_link()
    t_sent = link.now()
    _, first = send(link, "PULSE 1 200 0 100 0 20 0 0 0")
    start = next(m for m in first + read(link, 200) if isinstance(m, Event) and m.kind == "PSTART")
    assert 190 <= start.t_ms - t_sent <= 220


def test_rejections():
    link = armed_link()
    for line, why in [
        ("PULSE 1 0 50 600 0 0 0 0 20", "channel disabled"),
        ("PULSE 1 0 50 600 0 199 0 0 0", "exceeds fmax_n"),
        ("PULSE 1 0 400 600 300 50 0 0 0", "need rise+fall <= dur"),
        ("PULSE 1 0 50 2000 0 50 0 0 0", "dur > pulse_max_ms"),
        ("SET loop_ms 5", "disarm first"),
        ("SET fmax_n 250", "out of range"),
        ("BOGUS", "unknown command"),
    ]:
        ack, _ = send(link, line)
        assert not ack.ok and ack.detail == why, line
    send(link, "PULSE 1 0 50 600 0 50 0 0 0")
    ack, _ = send(link, "PULSE 2 0 50 600 0 50 0 0 0")
    assert ack.detail == "busy"


def test_abort_ramps_down_and_estop_zeroes():
    link = armed_link()
    send(link, "PULSE 1 0 0 800 0 95 0 0 0")
    read(link, 20)
    send(link, "ABORT")
    tel = [m for m in read(link, 10) if isinstance(m, Telemetry)]
    assert tel[-1].target["A"] == 5.0
    ack, _ = send(link, "STOP")
    assert ack.cmd == "ESTOP" and link.state == "ESTOP"
    tel = [m for m in read(link, 10) if isinstance(m, Telemetry)]
    assert all(t.target[c] == 0.0 and t.dac[c] == 0 for t in tel for c in "ABCD")
    ack, _ = send(link, "ARM")                            # recoverable, unlike v0
    assert ack.ok


def test_release_ends_disarmed():
    link = armed_link()
    send(link, "RELEASE 100")
    read(link, 40)
    assert link.state == "DISARMED"


def test_watchdog_aborts_pending_pulse():
    link = armed_link(wd_ms=100)
    _, first = send(link, "PULSE 1 5000 0 100 0 50 0 0 0")
    kinds = [m.kind for m in first + read(link, 100) if isinstance(m, Event)]
    assert "WD" in kinds and "PABORT" in kinds and "PSTART" not in kinds

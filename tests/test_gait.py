import math

from bumpem.gait import FS_NOISE, FS_VALID, TO_NOISE, TO_VALID, GaitDetector

FS_HZ = 1000


def running_grf(n_steps=10, step=0.33, stance=0.25, peak=1800.0):
    """Summed vertical GRF: half-sine stance, zero flight."""
    out = []
    for i in range(int(n_steps * step * FS_HZ)):
        t = i / FS_HZ
        ph = t % step
        out.append((t, peak * math.sin(math.pi * ph / stance) if ph < stance else 0.0))
    return out


def run(samples):
    det = GaitDetector()
    return det, [(t, e) for t, fz in samples if (e := det.update(t, fz))]


def test_counts_each_step():
    det, ev = run(running_grf())
    assert det.fs_count == 10
    assert sum(e == TO_VALID for _, e in ev) == 10


def test_rejects_spike_in_flight():
    s = running_grf(n_steps=2)
    # 5 ms 400 N spike 50 ms after first toe-off
    s = [(t, 400.0 if 0.30 <= t < 0.305 else fz) for t, fz in s]
    det, ev = run(s)
    kinds = [e for _, e in ev]
    assert FS_NOISE in kinds or TO_NOISE in kinds
    assert det.fs_count == 2

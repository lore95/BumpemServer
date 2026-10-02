import pytest
import random
from collections import Counter

from bumpem.experiment import Scheduler, make_sequence
from bumpem.gait import FS_VALID


def test_sequence_blocks_balanced():
    seq = make_sequence(rng=random.Random(0))
    assert len(seq) == 25
    for i in range(0, 25, 5):
        assert sorted(seq[i:i + 5]) == sorted(["a", "b", "c", "ab", "bc"])


def test_scheduler_fires_within_range():
    s = Scheduler(make_sequence(n_blocks=1), rng=random.Random(1))
    gaps, n = [], 0
    while not s.finished:
        n += 1
        if s.on_event(FS_VALID):
            gaps.append(n)
            n = 0
    assert len(gaps) == 5 and all(50 <= g <= 75 for g in gaps)
    assert s.on_event(FS_VALID) is None


def test_standin_recovery_delays_counting():
    from bumpem.recovery import FixedWaitRecovery
    s = Scheduler(["a", "b"], fs_min=3, fs_max=3, recovery=FixedWaitRecovery(wait_s=2.0),
                  rng=random.Random(0))
    step = 0.5                                   # one valid FS every 0.5 s
    fired = [t for t in (i * step for i in range(40)) if s.on_event(FS_VALID, t)]
    # 1st: 3rd FS (t=1.0). 2nd: recovered at t=3.0 (that FS counts) + 2 more → t=4.0
    assert fired == [1.0, 4.0]


def test_recovery_requires_time():
    from bumpem.recovery import FixedWaitRecovery
    s = Scheduler(["a"], recovery=FixedWaitRecovery(1.0))
    with pytest.raises(ValueError):
        s.on_event(FS_VALID)

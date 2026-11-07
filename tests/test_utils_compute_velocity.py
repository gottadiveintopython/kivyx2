from pytest import approx

from kivyx.utils import compute_velocity
    

def test_all_records_are_fresh():
    # (dx1 + dx2) / (t2 - t0) == (2 + 3) / (0.2 - 0) == 25.0
    assert compute_velocity([(0, 1, 0), (0.1, 2, 0), (0.2, 3, 0)], time_window=1) \
        == approx((25.0, 0.0))


def test_first_record_is_stale():
    # (dx1 + dx2) / (t2 - t0) == (2 + 3) / (0.2 - 0) == 25.0
    assert compute_velocity([(0, 1, 0), (0.1, 2, 0), (0.2, 3, 0)], time_window=0.15) \
        == approx((25.0, 0.0))


def test_first_two_records_are_stale():
    # dx2 / (t2 - t1) == 3 / (0.2 - 0.1) == 30.0
    assert compute_velocity([(0, 1, 0), (0.1, 2, 0), (0.2, 3, 0)], time_window=0.05) \
        == approx((30.0, 0.0))


def test_zero_duration():
    assert compute_velocity([(0, 1, 0), (0, 2, 0)], time_window=1, fallback=...) \
        is ...


def test_negative_duration():
    assert compute_velocity([(1, 1, 0), (0, 2, 0)], time_window=1, fallback=...) \
        is ...


def test_one_record():
    assert compute_velocity([(0, 1, 0)], time_window=1, fallback=...) \
        is ...

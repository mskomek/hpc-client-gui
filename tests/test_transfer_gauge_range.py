"""Native integer gauge boundaries, without importing wx or Qt."""
import pytest

from hpc_gui._wx_transfer_common import gauge_range_value


@pytest.mark.parametrize("done,total,expected", [
    (0, 0, (1, 0)),
    (-3, 100, (100, 0)),
    (101, 100, (100, 100)),
    (2**31 - 1, 2**31 - 1, (2**31 - 1, 2**31 - 1)),
    (2**31 - 1, 2**31, (10000, 9999)),
    (5 * 1024**3, 8 * 1024**3, (10000, 6250)),
    (8 * 1024**3, 8 * 1024**3, (10000, 10000)),
    (2**80 - 1, 2**80, (10000, 9999)),
])
def test_gauge_range_value(done, total, expected):
    assert gauge_range_value(done, total) == expected

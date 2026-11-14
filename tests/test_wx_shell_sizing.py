"""Shell window sizing: the minimum must fit the desktop it opens on."""

from __future__ import annotations

import pytest

from hpc_gui.wx_shell_sizing import (
    FLOOR_SIZE,
    MINIMUM_SIZE,
    PREFERRED_SIZE,
    clamp_size,
    shell_sizes,
)


@pytest.mark.unit
def test_large_desktop_keeps_the_spec_sizes():
    assert clamp_size(PREFERRED_SIZE, (2560, 1440)) == PREFERRED_SIZE
    assert clamp_size(MINIMUM_SIZE, (2560, 1440)) == MINIMUM_SIZE


@pytest.mark.unit
def test_small_desktop_is_clamped_to_the_work_area():
    available = (1024, 768)
    assert clamp_size(PREFERRED_SIZE, available) == (1024, 768)
    assert clamp_size(MINIMUM_SIZE, available) == (1024, 760)


@pytest.mark.unit
def test_floor_is_respected_when_the_work_area_can_fit_it():
    assert clamp_size((800, 500), (1920, 1080)) == FLOOR_SIZE


@pytest.mark.unit
@pytest.mark.parametrize("available", [(800, 600), (640, 480), (320, 200), (1, 1)])
def test_small_work_area_is_never_exceeded(available):
    assert clamp_size(PREFERRED_SIZE, available) == available
    assert clamp_size(MINIMUM_SIZE, available) == available


@pytest.mark.unit
def test_invalid_zero_area_does_not_create_a_zero_size_frame():
    assert clamp_size(PREFERRED_SIZE, (0, 0)) == (1, 1)


class _Area:
    def __init__(self, width, height):
        self.width = width
        self.height = height


class _Display:
    def __init__(self, area):
        self._area = area

    def GetClientArea(self):  # noqa: N802 - wx naming
        return self._area


class _FakeWx:
    def __init__(self, area):
        self._area = area

    def Display(self, _index=0):  # noqa: N802
        return _Display(self._area)


@pytest.mark.unit
def test_shell_sizes_follows_the_display():
    default, minimum = shell_sizes(_FakeWx(_Area(1024, 768)))
    assert default == (1024, 768)
    assert minimum == (1024, 760)

    default, minimum = shell_sizes(_FakeWx(_Area(1920, 1080)))
    assert default == PREFERRED_SIZE
    assert minimum == MINIMUM_SIZE


@pytest.mark.unit
def test_shell_sizes_for_very_small_display():
    preferred, minimum = shell_sizes(_FakeWx(_Area(640, 480)))
    assert preferred == (640, 480)
    assert minimum == (640, 480)


@pytest.mark.unit
def test_missing_display_falls_back_to_the_preferred_size():
    class Broken:
        def Display(self, _index=0):  # noqa: N802
            raise RuntimeError("no display")

    default, minimum = shell_sizes(Broken())
    assert default == PREFERRED_SIZE
    assert minimum == MINIMUM_SIZE

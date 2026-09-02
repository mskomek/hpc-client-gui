from hpc_gui.services.geometry_policy import Rect, recover_geometry


def test_geometry_clamps_and_recovers_removed_monitor():
    laptop = Rect(0, 0, 1366, 728)
    assert recover_geometry(Rect(2700, 100, 900, 650), (laptop,)) == Rect(466, 78, 900, 650)
    assert recover_geometry(Rect(10, 10, -1, 0), (laptop,)).width == 900


def test_geometry_clamps_large_window_and_preserves_visible_display():
    display = Rect(1920, 0, 1920, 1040)
    restored = recover_geometry(Rect(1800, -100, 3000, 1500), (display,))
    assert restored == Rect(1920, 0, 1920, 1040)

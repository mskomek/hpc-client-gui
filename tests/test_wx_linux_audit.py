import os

from hpc_gui.wx_runtime import environment_without_qt_graphics


def test_wx_runtime_drops_legacy_qt_graphics_environment():
    env = environment_without_qt_graphics(
        {**os.environ, "QTWEBENGINE_CHROMIUM_FLAGS": "--disable-gpu", "QTWEBENGINE_DISABLE_GPU": "1"}
    )
    assert "QTWEBENGINE_CHROMIUM_FLAGS" not in env
    assert "QTWEBENGINE_DISABLE_GPU" not in env

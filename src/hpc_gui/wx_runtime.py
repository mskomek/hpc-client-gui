"""Small runtime helpers for the optional wx application."""

from __future__ import annotations

import os


_QT_GRAPHICS_ENV = {
    "QTWEBENGINE_CHROMIUM_FLAGS",
    "QTWEBENGINE_DISABLE_GPU",
    "QTWEBENGINE_REMOTE_DEBUGGING",
}


def environment_without_qt_graphics(env: dict[str, str] | None = None) -> dict[str, str]:
    """Keep legacy Qt settings readable, but never pass them to a wx process."""
    clean = dict(os.environ if env is None else env)
    for name in _QT_GRAPHICS_ENV:
        clean.pop(name, None)
    return clean


__all__ = ["environment_without_qt_graphics"]

"""Small, framework-guarded message dialogs for non-UI layers.

Services and core modules must not import a GUI toolkit at module import
time.  These helpers use wx only when a ``wx.App`` exists and marshal calls
from worker threads onto the GUI thread; without wx they log and return a
safe default.
"""

from __future__ import annotations

import sys
import threading
from typing import Any, Optional


def _wx() -> Optional[Any]:
    try:
        import wx  # type: ignore[import-not-found]
    except Exception:
        return None
    try:
        return wx if wx.GetApp() is not None else None
    except Exception:
        return None


def wx_app_available() -> bool:
    return _wx() is not None


def _on_gui_thread(wx: Any, fn, *args):
    """Run ``fn`` on the GUI thread and return its result."""
    try:
        if wx.IsMainThread():
            return fn(*args)
    except Exception:
        return fn(*args)
    box: dict[str, Any] = {}
    done = threading.Event()

    def call():
        try:
            box["value"] = fn(*args)
        finally:
            done.set()

    wx.CallAfter(call)
    done.wait()
    return box.get("value")


def ask_yes_no(message: str, title: str, parent=None) -> bool:
    """YES/NO question; False when no wx.App is running."""
    wx = _wx()
    if wx is None:
        return False

    def ask():
        return wx.MessageBox(message, title, wx.YES_NO | wx.ICON_QUESTION, parent) == wx.YES

    try:
        return bool(_on_gui_thread(wx, ask))
    except Exception:
        return False


def show_error(message: str, title: str, parent=None) -> bool:
    """Error box when wx runs; otherwise stderr.  Returns True if shown in wx."""
    wx = _wx()
    if wx is not None:
        try:
            if wx.IsMainThread():
                wx.MessageBox(message, title, wx.OK | wx.ICON_ERROR, parent)
            else:
                wx.CallAfter(wx.MessageBox, message, title, wx.OK | wx.ICON_ERROR, parent)
            return True
        except Exception:
            pass
    try:
        print(f"{title}: {message}", file=sys.stderr)
    except Exception:
        pass
    return False

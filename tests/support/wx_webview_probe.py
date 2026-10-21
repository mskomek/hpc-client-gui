"""Bounded wx event pumping for subprocess isolated WebView contract tests."""

from __future__ import annotations

import time
from collections.abc import Callable


def wait_until_ready(wx, predicate: Callable[[], bool], timeout: float = 6.0) -> bool:
    """Run the native wx event loop until a WebView is ready or time expires."""
    app = wx.App.Get()
    if app is None:
        app = wx.App(False)

    deadline = time.monotonic() + timeout
    outcome = {"ready": False}

    def poll() -> None:
        if predicate():
            outcome["ready"] = True
            app.ExitMainLoop()
        elif time.monotonic() >= deadline:
            app.ExitMainLoop()
        else:
            wx.CallLater(25, poll)

    wx.CallAfter(poll)
    app.MainLoop()
    return outcome["ready"] or predicate()

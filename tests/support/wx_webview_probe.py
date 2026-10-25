"""Bounded wx event pumping for subprocess isolated WebView contract tests."""

from __future__ import annotations

import sys
import time
from collections.abc import Callable


def wait_until_ready(wx, predicate: Callable[[], bool], timeout: float = 6.0) -> bool:
    """Run wx's native event loop until WebView readiness or the deadline."""
    app = wx.App.Get()
    if app is None:
        app = wx.App(False)
    if predicate():
        return True

    deadline = time.monotonic() + timeout
    if sys.platform != "win32":
        while time.monotonic() < deadline:
            if predicate():
                return True
            wx.YieldIfNeeded()
            time.sleep(0.025)
        return bool(predicate())

    windows = wx.GetTopLevelWindows()
    if not windows:
        return False
    owner = windows[0]
    timer = wx.Timer(owner)

    def stop_when_ready(_event) -> None:
        if predicate() or time.monotonic() >= deadline:
            timer.Stop()
            app.ExitMainLoop()

    owner.Bind(wx.EVT_TIMER, stop_when_ready, timer)
    timer.Start(25)
    app.MainLoop()
    owner.Unbind(wx.EVT_TIMER, handler=stop_when_ready, source=timer)
    return bool(predicate())

"""Shared wx fixture and browser builder for remote file action tests."""

from __future__ import annotations

import time

import wx

from hpc_gui.core.i18n import load_language
from hpc_gui.wx_remote_files_view import show_remote_files


def start_app():
    load_language("en")
    app = wx.App.Get()
    if app is None:
        app = wx.App(False)
    return app


def close_app(app):
    for window in list(wx.GetTopLevelWindows()):
        if window and not window.IsBeingDeleted():
            window.Close()
    for _ in range(3):
        app.ProcessPendingEvents()
        wx.Yield()
    for window in list(wx.GetTopLevelWindows()):
        if window and not window.IsBeingDeleted():
            window.Destroy()
    app.ProcessPendingEvents()
    wx.Yield()
    assert not wx.GetTopLevelWindows(), "wx top-level windows survived fixture teardown"
    app.Destroy()


def pump(app, predicate, timeout=2):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.ProcessPendingEvents()
        if predicate():
            return
        wx.MilliSleep(5)
    app.ProcessPendingEvents()
    assert predicate()


def browser(app, backend, model=None, operation=None):
    show_remote_files(
        model=model,
        loader=backend.iterdir_entries,
        operation=operation or backend.operation,
    )
    frame = [window for window in wx.GetTopLevelWindows() if hasattr(window, "_wx_remote_controls")][-1]
    pump(app, lambda: frame._wx_remote_controls["listing"].GetItemCount() >= 1)
    return frame


__all__ = ["browser", "close_app", "pump", "start_app", "wx"]

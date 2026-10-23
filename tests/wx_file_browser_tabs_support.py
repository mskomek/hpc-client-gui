"""Shared wx fixture and browser launch helpers for tab lifecycle tests."""

from __future__ import annotations

import time

import pytest

wx = pytest.importorskip("wx")

from hpc_gui.wx_local_files import show_local_files
from hpc_gui.wx_remote_files import WxRemoteDirectoryModel
from hpc_gui.wx_remote_files_view import show_remote_files


def _pump(app, pred, timeout=5):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.ProcessPendingEvents()
        if pred():
            return
        wx.MilliSleep(5)
    app.ProcessPendingEvents()
    assert pred()


@pytest.fixture
def wx_app():
    from hpc_gui.core.i18n import load_language

    load_language("en")
    app = wx.App.Get()
    if app is None:
        app = wx.App(False)
    yield app
    for window in wx.GetTopLevelWindows():
        if window:
            window.Destroy()
    app.ProcessPendingEvents()
    wx.YieldIfNeeded()
    app.ProcessPendingEvents()
    app.Destroy()


def _local(app, path):
    show_local_files(path=path)
    frame = [window for window in wx.GetTopLevelWindows() if hasattr(window, "_wx_local_controls")][
        -1
    ]
    _pump(app, lambda: frame._wx_local_controls["listing"].GetItemCount() >= 0)
    return frame


def _remote(app, backend, path="/work"):
    show_remote_files(
        model=WxRemoteDirectoryModel(path),
        loader=backend.iterdir_entries,
        operation=backend.operation,
    )
    frame = [
        window for window in wx.GetTopLevelWindows() if hasattr(window, "_wx_remote_controls")
    ][-1]
    _pump(app, lambda: frame._wx_remote_controls["listing"].GetItemCount() >= 1)
    return frame

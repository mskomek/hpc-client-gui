"""Protect the process-wide wx.App used by the mixed GUI test suite."""

from __future__ import annotations

import pytest

wx = pytest.importorskip("wx")


@pytest.mark.wx
@pytest.mark.resource
def test_destroy_closes_windows_without_replacing_process_app():
    app = wx.App.Get() or wx.App(False)
    frame = wx.Frame(None, title="wx lifecycle regression")
    closed = []
    frame.Bind(wx.EVT_CLOSE, lambda event: (closed.append(True), event.Skip()))
    frame.Show()
    wx.YieldIfNeeded()

    app.Destroy()

    assert not list(wx.GetTopLevelWindows())
    assert closed == [True]
    assert wx.App.Get() is app
    assert wx.App(False) is app

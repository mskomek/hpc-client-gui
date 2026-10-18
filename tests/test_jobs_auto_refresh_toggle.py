"""Jobs polling control regression tests for the wx V2 screen."""

from __future__ import annotations

import time

import pytest

wx = pytest.importorskip("wx")

from hpc_gui.core.i18n import load_language  # noqa: E402
from hpc_gui.wx_jobs import show_jobs  # noqa: E402


@pytest.fixture
def wx_app():
    load_language("en")
    app = wx.App.Get() or wx.App(False)
    yield app
    for window in list(wx.GetTopLevelWindows()):
        try:
            window.Destroy()
        except Exception:
            pass
    app.ProcessPendingEvents()


def _pump(app, seconds: float) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        app.ProcessPendingEvents()
        wx.SafeYield()
        wx.MilliSleep(10)


def test_auto_refresh_checkbox_stops_jobs_polling_but_manual_refresh_works(wx_app):
    calls = []

    def list_jobs():
        calls.append(time.monotonic())
        return []

    show_jobs(list_jobs=list_jobs, read_output=lambda _job: "")
    frame = next(window for window in wx.GetTopLevelWindows() if hasattr(window, "_wx_jobs_controls"))
    _pump(wx_app, 0.2)
    assert calls

    checkbox = frame._wx_jobs_controls["cb_auto_refresh"]
    checkbox.SetValue(False)
    calls_after_uncheck = len(calls)
    _pump(wx_app, 1.3)
    assert len(calls) == calls_after_uncheck

    frame._wx_jobs_refresh_jobs()
    _pump(wx_app, 0.2)
    assert len(calls) == calls_after_uncheck + 1

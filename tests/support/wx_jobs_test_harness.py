"""Small shared wx helpers for Jobs workspace acceptance tests."""

from __future__ import annotations

import pytest

wx = pytest.importorskip("wx")

from hpc_gui.core.i18n import load_language  # noqa: E402
from hpc_gui.wx_jobs import build_jobs_panel  # noqa: E402


def jobs_fixture_rows():
    return [
        {
            "id": "1001", "name": "jobA", "state": "RUNNING", "partition": "gpu",
            "elapsed": "00:05:00", "nodes": "2", "cpus": "16", "reason": "None",
            "workdir": "/work/1001", "stdout_path": "/work/1001/out.txt",
            "stderr_path": "/work/1001/err.txt",
        },
        {
            "id": "1002", "name": "jobB", "state": "PENDING", "partition": "cpu",
            "elapsed": "-", "nodes": "1", "cpus": "4", "reason": "Priority",
            "workdir": "/work/1002",
        },
    ]


def build_workspace(**kwargs):
    load_language("en")
    app = wx.App.Get() or wx.App(False)
    frame = wx.Frame(None)
    panel = build_jobs_panel(
        frame, list_jobs=kwargs.pop("list_jobs", jobs_fixture_rows), **kwargs
    )
    frame.Show()
    wx.Yield()
    return app, frame, panel


def pump_wx(predicate, rounds=80):
    for _ in range(rounds):
        wx.Yield()
        if predicate():
            return True
        wx.MilliSleep(10)
    return bool(predicate())


def select_job(panel, index=0):
    jobs = panel._wx_jobs_controls["jobs"]
    event = wx.ListEvent(wx.wxEVT_LIST_ITEM_SELECTED, jobs.GetId())
    event.SetIndex(index)
    jobs.GetEventHandler().ProcessEvent(event)
    wx.Yield()


def click_button(control):
    event = wx.CommandEvent(wx.wxEVT_BUTTON, control.GetId())
    event.SetEventObject(control)
    control.GetEventHandler().ProcessEvent(event)
    wx.Yield()


def close_frame(frame):
    try:
        frame.Close()
    except Exception:
        pass
    for _ in range(4):
        wx.Yield()

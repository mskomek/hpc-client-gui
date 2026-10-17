import pytest
wx = pytest.importorskip("wx")
from hpc_gui.core.i18n import load_language, t
from hpc_gui.services.raw_command_result import RawCommandResult
from hpc_gui.wx_jobs import build_jobs_panel
def _fake_jobs():
    return [
        {"id": "1001", "state": "RUNNING", "name": "jobA", "partition": "gpu",
         "elapsed": "00:05:00", "nodes": "2", "cpus": "16", "reason": "None",
         "workdir": "/work/1001", "stdout_path": "/out/1001.out",
         "stderr_path": "/out/1001.err"},
        {"id": "1002", "state": "PENDING", "name": "jobB", "partition": "cpu",
         "elapsed": "-", "nodes": "1", "cpus": "4", "reason": "Priority"},
    ]
def _build_panel(**kwargs):
    app = wx.App.Get() or wx.App(False)
    frame = wx.Frame(None)
    panel = build_jobs_panel(frame, list_jobs=_fake_jobs, **kwargs)
    frame.Show()
    wx.Yield()
    return app, frame, panel
def _select_job(panel, index=0):
    ctrls = panel._wx_jobs_controls
    evt = wx.ListEvent(wx.wxEVT_LIST_ITEM_SELECTED, ctrls["jobs"].GetId())
    evt.SetIndex(index)
    ctrls["jobs"].GetEventHandler().ProcessEvent(evt)
    wx.Yield()
def _close(frame):
    try:
        for child in frame.GetChildren():
            if hasattr(child, "_wx_jobs_state"):
                child.Hide()
                child.Destroy()
        frame.Close()
    except Exception:
        pass
    for _ in range(3):
        wx.Yield()

__all__ = [
    'pytest',
    'wx',
    'load_language',
    't',
    'RawCommandResult',
    'build_jobs_panel',
    '_fake_jobs',
    '_build_panel',
    '_select_job',
    '_close',
]

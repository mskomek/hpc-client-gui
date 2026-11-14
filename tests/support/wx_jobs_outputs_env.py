"""Wave 50 Jobs Files/Outputs tabs real-event tests."""
import pytest
wx = pytest.importorskip("wx")
from hpc_gui.wx_jobs import build_jobs_panel


def _fake_jobs():
    return [
        {"id": "1001", "state": "RUNNING", "name": "jobA", "workdir": "/work", "stdout_path": "/out/1001.out", "stderr_path": "/out/1001.err"},
        {"id": "1002", "state": "PENDING", "name": "jobB", "workdir": "/work"},
    ]


def _build_panel(list_jobs=None, read_output=None, list_job_files=None, lifecycle=None, **kwargs):
    app = wx.App.Get() or wx.App(False)
    frame = wx.Frame(None)
    session_state = kwargs.get("session_state")
    if isinstance(session_state, dict) and "remote_files_callbacks" not in kwargs:
        from hpc_gui.wx_shell import _remote_files_callbacks
        kwargs["remote_files_callbacks"] = _remote_files_callbacks(session_state, frame, lifecycle)
    panel = build_jobs_panel(frame, list_jobs=list_jobs or (lambda: _fake_jobs()), read_output=read_output or (lambda j: {"stdout": f"out {j}", "stderr": f"err {j}"}), list_job_files=list_job_files or (lambda j: [{"name": f"file_{j}.txt", "size": "123", "path": f"/work/{j}/file.txt"}]), lifecycle=lifecycle, **kwargs)
    frame.Show()
    wx.Yield()
    return app, frame, panel


def _close(frame):
    try:
        for child in frame.GetChildren():
            if hasattr(child, "_wx_jobs_state"):
                try:
                    child.Hide()
                    child.Destroy()
                except Exception:
                    pass
        frame.Close()
    except Exception:
        pass
    for _ in range(3):
        wx.Yield()
    try:
        if not frame.IsBeingDeleted():
            frame.Destroy()
    except Exception:
        pass
    for _ in range(3):
        wx.Yield()

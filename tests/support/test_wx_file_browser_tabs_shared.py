import time
import threading
from pathlib import Path, PurePosixPath
import pytest
wx = pytest.importorskip("wx")
from hpc_gui.wx_local_files import LocalBrowserModel, LocalEntry, show_local_files
from hpc_gui.wx_remote_files import RemoteEntry, WxRemoteDirectoryModel
from hpc_gui.wx_remote_files_view import show_remote_files
from mock_hpc_files import MockRemoteFilesBackend
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
    for w in wx.GetTopLevelWindows():
        if w:
            w.Destroy()
    app.ProcessPendingEvents()
    wx.YieldIfNeeded()
    app.ProcessPendingEvents()
    app.Destroy()
def _local(app, path):
    show_local_files(path=path)
    frame = [w for w in wx.GetTopLevelWindows() if hasattr(w, "_wx_local_controls")][-1]
    _pump(app, lambda: frame._wx_local_controls["listing"].GetItemCount() >= 0)
    return frame
def _remote(app, backend, path="/work"):
    show_remote_files(model=WxRemoteDirectoryModel(path), loader=backend.iterdir_entries, operation=backend.operation)
    frame = [w for w in wx.GetTopLevelWindows() if hasattr(w, "_wx_remote_controls")][-1]
    _pump(app, lambda: frame._wx_remote_controls["listing"].GetItemCount() >= 1)
    return frame

__all__ = [
    'time',
    'threading',
    'Path',
    'PurePosixPath',
    'pytest',
    'wx',
    'LocalBrowserModel',
    'LocalEntry',
    'show_local_files',
    'RemoteEntry',
    'WxRemoteDirectoryModel',
    'show_remote_files',
    'MockRemoteFilesBackend',
    '_pump',
    'wx_app',
    '_local',
    '_remote',
]

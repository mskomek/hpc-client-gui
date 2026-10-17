import threading
import time
from pathlib import Path
import pytest
wx = pytest.importorskip("wx")
from hpc_gui.wx_local_files import LocalBrowserModel, LocalEntry, show_local_files
from hpc_gui.wx_remote_files import RemoteEntry, WxRemoteDirectoryModel
from hpc_gui.wx_remote_files_view import build_remote_files_panel, show_remote_files
from mock_hpc_files import MockRemoteFilesBackend
def _pump(app, predicate, timeout=2):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.ProcessPendingEvents()
        if predicate():
            return
        wx.MilliSleep(5)
    app.ProcessPendingEvents()
    assert predicate()
@pytest.fixture
def wx_app():
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
    frame = [window for window in wx.GetTopLevelWindows() if hasattr(window, "_wx_local_controls")][-1]
    _pump(app, lambda: frame._wx_local_controls["listing"].GetItemCount() >= 1)
    return frame
def _remote(app, backend, operation):
    show_remote_files(model=WxRemoteDirectoryModel("/work"), loader=backend.iterdir_entries, operation=operation)
    frame = [window for window in wx.GetTopLevelWindows() if hasattr(window, "_wx_remote_controls")][-1]
    _pump(app, lambda: frame._wx_remote_controls["listing"].GetItemCount() >= 1)
    return frame
class _Dialog:
    def __init__(self, value):
        self.value = value

    def ShowModal(self):
        return wx.ID_OK

    def GetValue(self):
        return self.value

    def Destroy(self):
        pass

__all__ = [
    'threading',
    'time',
    'Path',
    'pytest',
    'wx',
    'LocalBrowserModel',
    'LocalEntry',
    'show_local_files',
    'RemoteEntry',
    'WxRemoteDirectoryModel',
    'build_remote_files_panel',
    'show_remote_files',
    'MockRemoteFilesBackend',
    '_pump',
    'wx_app',
    '_local',
    '_remote',
    '_Dialog',
]

import threading
import time
import pytest
wx = pytest.importorskip("wx")
from mock_hpc_files import MockRemoteFilesBackend
from support.wx_clipboard import read_clipboard_text
from hpc_gui.services.file_clipboard import get_file_clipboard
from hpc_gui.core.i18n import load_language
from hpc_gui.wx_remote_files import WxRemoteDirectoryModel
from hpc_gui.wx_remote_files_view import show_remote_files
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
    load_language("en")
    app = wx.App.Get()
    if app is None:
        app = wx.App(False)
    yield app
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
def _browser(app, backend, model=None, operation=None):
    show_remote_files(model=model, loader=backend.iterdir_entries, operation=operation or backend.operation)
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
class _FileDialog(_Dialog):
    def GetPaths(self):
        return self.value
class _DestinationDialog(_Dialog):
    def GetPath(self):
        return self.value

__all__ = [
    'threading',
    'time',
    'pytest',
    'wx',
    'MockRemoteFilesBackend',
    'read_clipboard_text',
    'get_file_clipboard',
    'load_language',
    'WxRemoteDirectoryModel',
    'show_remote_files',
    '_pump',
    'wx_app',
    '_browser',
    '_Dialog',
    '_FileDialog',
    '_DestinationDialog',
]

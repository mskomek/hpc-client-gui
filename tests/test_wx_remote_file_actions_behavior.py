import threading
import time

import pytest

wx = pytest.importorskip("wx")

from mock_hpc_files import MockRemoteFilesBackend
from hpc_gui.services.file_clipboard import get_file_clipboard
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
    app = wx.App(False)
    yield app
    for window in wx.GetTopLevelWindows():
        if window:
            window.Destroy()
    app.ProcessPendingEvents()
    app.Destroy()


def _browser(app, backend, model=None):
    show_remote_files(model=model, loader=backend.iterdir_entries, operation=backend.operation)
    frame = [window for window in wx.GetTopLevelWindows() if hasattr(window, "_wx_remote_controls")][-1]
    _pump(app, lambda: frame._wx_remote_controls["listing"].GetItemCount() >= 1)
    return frame


def test_remote_move_and_upload_actions_reach_backend_off_gui_thread(wx_app, monkeypatch):
    backend = MockRemoteFilesBackend()
    frame = _browser(wx_app, backend)
    gui_thread = threading.get_ident()
    monkeypatch.setattr(wx, "TextEntryDialog", lambda *_args, **_kwargs: _Dialog("/work"))
    monkeypatch.setattr(wx, "FileDialog", lambda *_args, **_kwargs: _FileDialog(("local.txt",)))
    frame._wx_remote_run_action("move", ("/work/a.txt",), "/work")
    _pump(wx_app, lambda: len(backend.calls) >= 1 and not frame._wx_remote_state["busy"])
    frame._wx_remote_run_action("upload", (), "/work")
    _pump(wx_app, lambda: len(backend.calls) >= 2)
    assert any(call[0] == "move" for call in backend.calls)
    assert any(call[0] == "upload" for call in backend.calls)
    assert all(thread_id != gui_thread for thread_id in backend.thread_ids)


def test_remote_new_folder_uses_clicked_directory_target(wx_app, monkeypatch):
    backend = MockRemoteFilesBackend()
    frame = _browser(wx_app, backend)
    monkeypatch.setattr(wx, "TextEntryDialog", lambda *_args, **_kwargs: _Dialog("child"))
    frame._wx_remote_run_action("new_folder", ("/work",), "/work")
    _pump(wx_app, lambda: ("mkdir", "/work/child") in backend.calls)
    assert "/work/child" in backend.entries


def test_wx_remote_keyboard_copy_and_paste_use_shared_clipboard(wx_app):
    backend = MockRemoteFilesBackend()
    backend.entries["/work/dest"] = True
    frame = _browser(wx_app, backend, WxRemoteDirectoryModel("/work"))
    listing = frame._wx_remote_controls["listing"]
    listing.Select(0)
    copy_event = wx.KeyEvent(wx.wxEVT_KEY_DOWN)
    copy_event.SetKeyCode(ord("C"))
    copy_event.SetControlDown(True)
    listing.ProcessEvent(copy_event)
    assert get_file_clipboard().get().paths == ["/work/a.txt"]
    frame._wx_remote_run_action("paste", (), "/work/dest")
    _pump(wx_app, lambda: ("copy", "/work/a.txt", "/work/dest/a.txt") in backend.calls)


def test_wx_remote_copy_path_uses_system_clipboard_without_backend(wx_app):
    backend = MockRemoteFilesBackend()
    frame = _browser(wx_app, backend, WxRemoteDirectoryModel("/work"))
    listing = frame._wx_remote_controls["listing"]
    listing.Select(0)
    frame._wx_remote_run_action("copy_path", ("/work",), "/")
    assert wx.TheClipboard.Open()
    try:
        data = wx.TextDataObject()
        assert wx.TheClipboard.GetData(data)
        assert data.GetText() == "/work"
    finally:
        wx.TheClipboard.Close()
    assert not any(call[0] in {"copy", "move"} for call in backend.calls)


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

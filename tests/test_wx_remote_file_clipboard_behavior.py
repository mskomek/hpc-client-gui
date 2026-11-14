import time

import pytest

wx = pytest.importorskip("wx")
pytestmark = [pytest.mark.gui, pytest.mark.wx]

from mock_hpc_files import MockRemoteFilesBackend
from support.wx_clipboard import read_clipboard_text
from hpc_gui.services.file_clipboard import get_file_clipboard
from hpc_gui.core.i18n import load_language
from hpc_gui.wx_remote_files import WxRemoteDirectoryModel
from hpc_gui.wx_remote_files_view import show_remote_files


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


def _pump(app, predicate, timeout=2):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.ProcessPendingEvents()
        if predicate():
            return
        wx.MilliSleep(5)
    app.ProcessPendingEvents()
    assert predicate()


def _browser(app, backend, model=None, operation=None):
    show_remote_files(model=model, loader=backend.iterdir_entries, operation=operation or backend.operation)
    frame = [window for window in wx.GetTopLevelWindows() if hasattr(window, "_wx_remote_controls")][-1]
    _pump(app, lambda: frame._wx_remote_controls["listing"].GetItemCount() >= 1)
    return frame


def test_wx_remote_keyboard_copy_and_paste_use_shared_clipboard(wx_app):
    backend = MockRemoteFilesBackend()
    backend.entries["/work/dest"] = True
    frame = _browser(wx_app, backend, WxRemoteDirectoryModel("/work"))
    listing = frame._wx_remote_controls["listing"]
    file_index = next(i for i in range(listing.GetItemCount()) if listing.GetItemText(i) == "a.txt")
    listing.Select(file_index)
    copy_event = wx.KeyEvent(wx.wxEVT_KEY_DOWN)
    copy_event.SetKeyCode(ord("C"))
    copy_event.SetControlDown(True)
    listing.ProcessEvent(copy_event)
    assert get_file_clipboard().get().paths == ["/work/a.txt"]
    frame._wx_remote_run_action("paste", (), "/work/dest")
    _pump(wx_app, lambda: ("copy", "/work/a.txt", "/work/dest/a.txt") in backend.calls)
def test_wx_remote_multi_item_paste_preserves_all_destinations(wx_app):
    backend = MockRemoteFilesBackend()
    backend.entries["/work/dest"] = True
    frame = _browser(wx_app, backend, WxRemoteDirectoryModel("/work"))
    get_file_clipboard().set("copy", ["/work/a.txt", "/work/b.txt"])
    frame._wx_remote_run_action("paste", (), "/work/dest")
    _pump(
        wx_app,
        lambda: not frame._wx_remote_state["busy"]
        and ("copy", "/work/a.txt", "/work/dest/a.txt") in backend.calls
        and ("copy", "/work/b.txt", "/work/dest/b.txt") in backend.calls,
    )
    assert len([call for call in backend.calls if call[0] == "copy"]) == 2
def test_wx_remote_ctrl_a_selects_all_rows(wx_app):
    backend = MockRemoteFilesBackend()
    backend.entries.update({"/work/folder": True})
    frame = _browser(wx_app, backend, WxRemoteDirectoryModel("/work"))
    listing = frame._wx_remote_controls["listing"]
    event = wx.KeyEvent(wx.wxEVT_KEY_DOWN)
    event.SetKeyCode(ord("A"))
    event.SetControlDown(True)
    listing.ProcessEvent(event)
    parent = next(i for i in range(listing.GetItemCount()) if listing.GetItemText(i) == "..")
    assert not listing.IsSelected(parent)
    assert all(
        listing.IsSelected(index)
        for index in range(listing.GetItemCount())
        if index != parent
    )
def test_wx_remote_copy_path_uses_system_clipboard_without_backend(wx_app):
    backend = MockRemoteFilesBackend()
    frame = _browser(wx_app, backend, WxRemoteDirectoryModel("/work"))
    listing = frame._wx_remote_controls["listing"]
    file_index = next(i for i in range(listing.GetItemCount()) if listing.GetItemText(i) == "a.txt")
    listing.Select(file_index)
    frame._wx_remote_run_action("copy_path", ("/work",), "/")
    assert read_clipboard_text() == "/work"
    assert not any(call[0] in {"copy", "move"} for call in backend.calls)
def test_wx_remote_copy_path_preserves_multiple_selected_paths(wx_app):
    backend = MockRemoteFilesBackend()
    frame = _browser(wx_app, backend, WxRemoteDirectoryModel("/work"))
    listing = frame._wx_remote_controls["listing"]
    file_indices = [
        next(i for i in range(listing.GetItemCount()) if listing.GetItemText(i) == name)
        for name in ("a.txt", "b.txt")
    ]
    listing.Select(file_indices[0])
    listing.Select(file_indices[1])
    frame._wx_remote_run_action("copy_path", ("/work/a.txt", "/work/b.txt"), "/work")
    assert read_clipboard_text().splitlines() == ["/work/a.txt", "/work/b.txt"]
    assert not backend.calls
def test_wx_remote_keyboard_cut_and_undo_leaves_pending_clipboard_untouched(wx_app):
    backend = MockRemoteFilesBackend()
    frame = _browser(wx_app, backend, WxRemoteDirectoryModel("/work"))
    listing = frame._wx_remote_controls["listing"]
    file_index = next(i for i in range(listing.GetItemCount()) if listing.GetItemText(i) == "a.txt")
    listing.Select(file_index)
    cut_event = wx.KeyEvent(wx.wxEVT_KEY_DOWN)
    cut_event.SetKeyCode(ord("X"))
    cut_event.SetControlDown(True)
    listing.ProcessEvent(cut_event)
    assert get_file_clipboard().get().op == "move"
    undo_event = wx.KeyEvent(wx.wxEVT_KEY_DOWN)
    undo_event.SetKeyCode(ord("Z"))
    undo_event.SetControlDown(True)
    listing.ProcessEvent(undo_event)
    assert get_file_clipboard().get().paths == ["/work/a.txt"]

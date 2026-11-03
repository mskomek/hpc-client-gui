"""Remote wx clipboard and navigation behavior across real UI events."""

import time

import pytest

wx = pytest.importorskip("wx")
pytestmark = [pytest.mark.gui, pytest.mark.wx]

from hpc_gui.core.i18n import load_language
from hpc_gui.services.file_clipboard import get_file_clipboard
from hpc_gui.wx_remote_files import WxRemoteDirectoryModel
from hpc_gui.wx_remote_files_view import show_remote_files
from mock_hpc_files import MockRemoteFilesBackend
from support.wx_listing_rows import content_rows, select_content_row


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
    app = wx.App.Get() or wx.App(False)
    yield app
    for window in list(wx.GetTopLevelWindows()):
        if window and not window.IsBeingDeleted():
            window.Destroy()
    app.ProcessPendingEvents()
    wx.Yield()
    assert not wx.GetTopLevelWindows()
    app.Destroy()


def _browser(app, backend, model=None, **kwargs):
    show_remote_files(
        model=model or WxRemoteDirectoryModel("/work"),
        loader=backend.iterdir_entries,
        operation=kwargs.get("operation", backend.operation),
        provider_filters=kwargs.get("provider_filters"),
    )
    frame = [window for window in wx.GetTopLevelWindows() if hasattr(window, "_wx_remote_controls")][-1]
    _pump(app, lambda: len(content_rows(frame._wx_remote_controls["listing"])) >= 1)
    return frame


def _capture_system_clipboard(monkeypatch):
    class Clipboard:
        text = ""

        def Open(self):
            return True

        def SetData(self, value):
            self.text = value.GetText()
            return True

        def Close(self):
            return None

    clipboard = Clipboard()
    monkeypatch.setattr(wx, "TheClipboard", clipboard)
    return clipboard


def test_remote_keyboard_copy_and_paste_use_shared_clipboard(wx_app):
    backend = MockRemoteFilesBackend()
    backend.entries["/work/dest"] = True
    frame = _browser(wx_app, backend)
    listing = frame._wx_remote_controls["listing"]
    select_content_row(listing, "a.txt")
    event = wx.KeyEvent(wx.wxEVT_KEY_DOWN)
    event.SetKeyCode(ord("C"))
    event.SetControlDown(True)
    listing.ProcessEvent(event)
    clipboard = get_file_clipboard().get()
    assert clipboard and clipboard.paths == ["/work/a.txt"]
    frame._wx_remote_run_action("paste", (), "/work/dest")
    _pump(wx_app, lambda: ("copy", "/work/a.txt", "/work/dest/a.txt") in backend.calls)


def test_remote_copy_path_uses_system_clipboard_without_backend(wx_app, monkeypatch):
    backend = MockRemoteFilesBackend()
    frame = _browser(wx_app, backend)
    listing = frame._wx_remote_controls["listing"]
    select_content_row(listing, "a.txt")
    clipboard = _capture_system_clipboard(monkeypatch)
    frame._wx_remote_run_action("copy_path", ("/work/a.txt",), "/work")
    assert clipboard.text == "/work/a.txt"
    assert not any(call[0] in {"copy", "move"} for call in backend.calls)


def test_remote_copy_path_preserves_multiple_selected_paths(wx_app, monkeypatch):
    backend = MockRemoteFilesBackend()
    frame = _browser(wx_app, backend)
    listing = frame._wx_remote_controls["listing"]
    select_content_row(listing, "a.txt")
    listing.Select(next(index for index, name in content_rows(listing) if name == "b.txt"))
    clipboard = _capture_system_clipboard(monkeypatch)
    frame._wx_remote_run_action("copy_path", ("/work/a.txt", "/work/b.txt"), "/work")
    assert clipboard.text.splitlines() == ["/work/a.txt", "/work/b.txt"]
    assert not backend.calls


def test_remote_keyboard_cut_sets_move_clipboard_without_undoing_it(wx_app):
    backend = MockRemoteFilesBackend()
    frame = _browser(wx_app, backend)
    listing = frame._wx_remote_controls["listing"]
    select_content_row(listing, "a.txt")
    cut = wx.KeyEvent(wx.wxEVT_KEY_DOWN)
    cut.SetKeyCode(ord("X"))
    cut.SetControlDown(True)
    listing.ProcessEvent(cut)
    clipboard = get_file_clipboard().get()
    assert clipboard and clipboard.op == "move" and clipboard.paths == ["/work/a.txt"]
    assert "/work/a.txt" in backend.entries


def test_remote_sort_and_provider_filter_preserve_navigation_rows(wx_app):
    backend = MockRemoteFilesBackend()
    backend.entries.update({
        "/work/Folder A": True, "/work/Folder B": True,
        "/work/z.txt": False, "/work/run.log": False,
        "/work/sub": True, "/work/sub/child.txt": False,
    })
    frame = _browser(wx_app, backend, provider_filters=[{
        "id": "logs", "labels": {"en": "Logs", "tr": "Günlükler"},
        "suffixes": [".log"], "order": 100,
    }])
    controls = frame._wx_remote_controls
    listing = controls["listing"]
    for _ in range(2):
        event = wx.ListEvent(wx.wxEVT_LIST_COL_CLICK, listing.GetId())
        event.SetColumn(0)
        event.SetEventObject(listing)
        listing.GetEventHandler().ProcessEvent(event)
    names = [name for _, name in content_rows(listing)]
    assert names[:3] == ["sub", "Folder B", "Folder A"]
    assert set(names[3:]) == {"z.txt", "run.log", "a.txt", "b.txt"}

    tab = frame._wx_remote_tabs[0]
    filter_nb = tab["filter_notebook"]
    assert "Logs" in [filter_nb.GetPageText(index) for index in range(filter_nb.GetPageCount())]
    filter_nb.SetSelection(tab["filter_ids"].index("logs"))
    wx_app.ProcessPendingEvents()
    assert [name for _, name in content_rows(listing)] == ["run.log"]

    controls["navigate"]("/work/sub")
    controls["load"]()
    _pump(wx_app, lambda: controls["path"].GetValue() == "/work/sub")
    controls["btn_back"].ProcessEvent(wx.CommandEvent(wx.wxEVT_BUTTON, controls["btn_back"].GetId()))
    _pump(wx_app, lambda: controls["path"].GetValue() == "/work")
    controls["btn_forward"].ProcessEvent(wx.CommandEvent(wx.wxEVT_BUTTON, controls["btn_forward"].GetId()))
    _pump(wx_app, lambda: controls["path"].GetValue() == "/work/sub")

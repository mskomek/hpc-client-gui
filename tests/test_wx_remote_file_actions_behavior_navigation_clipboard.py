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
    frame.SetSize(wx.Size(1100, 760))
    frame.Show()
    frame.Layout()
    frame.SendSizeEvent()
    _pump(app, lambda: frame._wx_remote_controls["listing"].GetItemCount() >= 1)
    frame.Layout()
    return frame

def test_wx_remote_keyboard_copy_and_paste_use_shared_clipboard(wx_app):
    backend = MockRemoteFilesBackend()
    backend.entries["/work/dest"] = True
    frame = _browser(wx_app, backend, WxRemoteDirectoryModel("/work"))
    listing = frame._wx_remote_controls["listing"]
    listing.Select(next(index for index in range(listing.GetItemCount()) if listing.GetItemText(index) == "a.txt"))
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
    parent_rows = [index for index in range(listing.GetItemCount()) if listing.GetItemText(index) == ".."]
    selectable_rows = [index for index in range(listing.GetItemCount()) if index not in parent_rows]
    assert len(parent_rows) == 1
    assert all(not listing.IsSelected(index) for index in parent_rows)
    assert selectable_rows
    assert all(listing.IsSelected(index) for index in selectable_rows)

def test_wx_remote_copy_path_uses_system_clipboard_without_backend(wx_app):
    backend = MockRemoteFilesBackend()
    frame = _browser(wx_app, backend, WxRemoteDirectoryModel("/work"))
    listing = frame._wx_remote_controls["listing"]
    listing.Select(next(index for index in range(listing.GetItemCount()) if listing.GetItemText(index) == "a.txt"))
    frame._wx_remote_run_action("copy_path", ("/work",), "/")
    assert read_clipboard_text() == "/work"
    assert not any(call[0] in {"copy", "move"} for call in backend.calls)

def test_wx_remote_copy_path_preserves_multiple_selected_paths(wx_app):
    backend = MockRemoteFilesBackend()
    frame = _browser(wx_app, backend, WxRemoteDirectoryModel("/work"))
    listing = frame._wx_remote_controls["listing"]
    listing.Select(0)
    listing.Select(1)
    frame._wx_remote_run_action("copy_path", ("/work/a.txt", "/work/b.txt"), "/work")
    assert read_clipboard_text().splitlines() == ["/work/a.txt", "/work/b.txt"]
    assert not backend.calls

def test_wx_remote_keyboard_cut_and_undo_leaves_pending_clipboard_untouched(wx_app):
    backend = MockRemoteFilesBackend()
    frame = _browser(wx_app, backend, WxRemoteDirectoryModel("/work"))
    listing = frame._wx_remote_controls["listing"]
    listing.Select(next(index for index in range(listing.GetItemCount()) if listing.GetItemText(index) == "a.txt"))
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

def test_wx_remote_backspace_navigates_parent_and_f5_refreshes(wx_app):
    backend = MockRemoteFilesBackend()
    frame = _browser(wx_app, backend, WxRemoteDirectoryModel("/work"))
    listing = frame._wx_remote_controls["listing"]
    back_event = wx.KeyEvent(wx.wxEVT_KEY_DOWN)
    back_event.SetKeyCode(wx.WXK_BACK)
    listing.ProcessEvent(back_event)
    assert frame._wx_remote_controls["path"].GetValue() == "/"
    _pump(wx_app, lambda: not frame._wx_remote_state["busy"] and listing.GetItemCount() >= 1)
    calls = backend.list_calls
    refresh_event = wx.KeyEvent(wx.wxEVT_KEY_DOWN)
    refresh_event.SetKeyCode(wx.WXK_F5)
    listing.ProcessEvent(refresh_event)
    _pump(wx_app, lambda: backend.list_calls > calls)

def test_wx_remote_paste_failure_is_visible_and_recovers(wx_app, monkeypatch):
    backend = MockRemoteFilesBackend()
    errors = []

    def failing_operation(_action, _paths, _destination=""):
        raise RuntimeError("paste failed")

    frame = _browser(wx_app, backend, WxRemoteDirectoryModel("/work"), failing_operation)
    listing = frame._wx_remote_controls["listing"]
    listing.Select(0)
    get_file_clipboard().set("copy", ["/work/a.txt"])
    monkeypatch.setattr(wx, "MessageBox", lambda message, *_args, **_kwargs: errors.append(message) or wx.OK)
    frame._wx_remote_run_action("paste", (), "/work")
    _pump(wx_app, lambda: not frame._wx_remote_state["busy"])
    assert errors == ["paste failed"]
    assert listing.IsEnabled()

def test_wx_remote_background_context_shows_directory_actions(wx_app, monkeypatch):
    backend = MockRemoteFilesBackend()
    frame = _browser(wx_app, backend)
    listing = frame._wx_remote_controls["listing"]
    labels = []
    listing.PopupMenu = lambda menu: labels.extend(item.GetItemLabelText() for item in menu.GetMenuItems())
    position = listing.ClientToScreen(wx.Point(5, max(5, listing.GetSize().height - 5)))
    event = wx.ContextMenuEvent(wx.wxEVT_CONTEXT_MENU, listing.GetId())
    event.SetPosition(position)
    listing.ProcessEvent(event)
    assert "Upload" in labels
    assert "New Folder" in labels
    assert "Refresh" in labels
    assert "Edit" not in labels and "Rename" not in labels

def test_wx_remote_background_upload_targets_current_directory(wx_app, monkeypatch):
    backend = MockRemoteFilesBackend()
    frame = _browser(wx_app, backend)
    listing = frame._wx_remote_controls["listing"]
    monkeypatch.setattr(wx, "FileDialog", lambda *_args, **_kwargs: _FileDialog(("local.txt",)))

    def choose_upload(menu):
        item = next(item for item in menu.GetMenuItems() if item.GetItemLabelText() == "Upload")
        event = wx.CommandEvent(wx.wxEVT_MENU, item.GetId())
        listing.ProcessEvent(event)

    listing.PopupMenu = choose_upload
    position = listing.ClientToScreen(wx.Point(5, max(5, listing.GetSize().height - 5)))
    event = wx.ContextMenuEvent(wx.wxEVT_CONTEXT_MENU, listing.GetId())
    event.SetPosition(position)
    listing.ProcessEvent(event)
    _pump(wx_app, lambda: ("upload", "local.txt", "/") in backend.calls)

def test_wx_remote_background_context_paste_targets_current_directory(wx_app):
    backend = MockRemoteFilesBackend()
    frame = _browser(wx_app, backend, WxRemoteDirectoryModel("/work"))
    get_file_clipboard().set("copy", ["/work/a.txt"])
    listing = frame._wx_remote_controls["listing"]

    def choose_paste(menu):
        item = next(item for item in menu.GetMenuItems() if item.GetItemLabelText() == "Paste")
        listing.ProcessEvent(wx.CommandEvent(wx.wxEVT_MENU, item.GetId()))

    listing.PopupMenu = choose_paste
    position = listing.ClientToScreen(wx.Point(5, max(5, listing.GetSize().height - 5)))
    event = wx.ContextMenuEvent(wx.wxEVT_CONTEXT_MENU, listing.GetId())
    event.SetPosition(position)
    listing.ProcessEvent(event)
    _pump(wx_app, lambda: ("copy", "/work/a.txt", "/work/a.txt") in backend.calls)

def test_wx_remote_clicked_directory_context_paste_targets_clicked_directory(wx_app):
    backend = MockRemoteFilesBackend()
    backend.entries["/work/dest"] = True
    frame = _browser(wx_app, backend, WxRemoteDirectoryModel("/work"))
    get_file_clipboard().set("copy", ["/work/a.txt"])
    listing = frame._wx_remote_controls["listing"]
    row = next(index for index in range(listing.GetItemCount()) if listing.GetItemText(index) == "dest")

    def choose_paste(menu):
        item = next(item for item in menu.GetMenuItems() if item.GetItemLabelText() == "Paste")
        listing.ProcessEvent(wx.CommandEvent(wx.wxEVT_MENU, item.GetId()))

    listing.PopupMenu = choose_paste
    position = listing.ClientToScreen(listing.GetItemPosition(row))
    event = wx.ContextMenuEvent(wx.wxEVT_CONTEXT_MENU, listing.GetId())
    event.SetPosition(position)
    listing.ProcessEvent(event)
    _pump(wx_app, lambda: ("copy", "/work/a.txt", "/work/dest/a.txt") in backend.calls)

def test_wx_remote_clicked_directory_context_cut_paste_moves_to_clicked_directory(wx_app):
    backend = MockRemoteFilesBackend()
    backend.entries["/work/dest"] = True
    frame = _browser(wx_app, backend, WxRemoteDirectoryModel("/work"))
    get_file_clipboard().set("move", ["/work/a.txt"])
    listing = frame._wx_remote_controls["listing"]
    row = next(index for index in range(listing.GetItemCount()) if listing.GetItemText(index) == "dest")

    def choose_paste(menu):
        item = next(item for item in menu.GetMenuItems() if item.GetItemLabelText() == "Paste")
        listing.ProcessEvent(wx.CommandEvent(wx.wxEVT_MENU, item.GetId()))

    listing.PopupMenu = choose_paste
    position = listing.ClientToScreen(listing.GetItemPosition(row))
    event = wx.ContextMenuEvent(wx.wxEVT_CONTEXT_MENU, listing.GetId())
    event.SetPosition(position)
    listing.ProcessEvent(event)
    _pump(wx_app, lambda: ("move", "/work/a.txt", "/work/dest/a.txt") in backend.calls)
    assert "/work/a.txt" not in backend.entries
    assert "/work/dest/a.txt" in backend.entries
    _pump(wx_app, lambda: not frame._wx_remote_state["busy"])
    undo = wx.KeyEvent(wx.wxEVT_KEY_DOWN)
    undo.SetKeyCode(ord("Z"))
    undo.SetControlDown(True)
    listing.ProcessEvent(undo)
    _pump(wx_app, lambda: ("move", "/work/dest/a.txt", "/work/a.txt") in backend.calls)
    assert "/work/a.txt" in backend.entries
    assert "/work/dest/a.txt" not in backend.entries

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

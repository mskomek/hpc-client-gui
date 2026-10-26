"""Remote file selection and clipboard interaction tests."""

import pytest

wx = pytest.importorskip("wx")
pytestmark = [pytest.mark.gui, pytest.mark.wx]

from mock_hpc_files import MockRemoteFilesBackend
from hpc_gui.services.file_clipboard import get_file_clipboard
from hpc_gui.wx_remote_files import WxRemoteDirectoryModel
from support.wx_remote_action_harness import browser, close_app, pump, start_app


@pytest.fixture
def wx_app():
    app = start_app()
    yield app
    close_app(app)


def test_keyboard_copy_and_paste_use_shared_clipboard(wx_app):
    backend = MockRemoteFilesBackend()
    backend.entries["/work/dest"] = True
    frame = browser(wx_app, backend, WxRemoteDirectoryModel("/work"))
    listing = frame._wx_remote_controls["listing"]
    row = next(index for index in range(listing.GetItemCount()) if listing.GetItemText(index) == "a.txt")
    listing.Select(row)
    copy_event = wx.KeyEvent(wx.wxEVT_KEY_DOWN)
    copy_event.SetKeyCode(ord("C"))
    copy_event.SetControlDown(True)
    listing.ProcessEvent(copy_event)
    assert get_file_clipboard().get().paths == ["/work/a.txt"]
    frame._wx_remote_run_action("paste", (), "/work/dest")
    pump(wx_app, lambda: ("copy", "/work/a.txt", "/work/dest/a.txt") in backend.calls)


def test_multi_item_paste_preserves_all_destinations(wx_app):
    backend = MockRemoteFilesBackend()
    backend.entries["/work/dest"] = True
    frame = browser(wx_app, backend, WxRemoteDirectoryModel("/work"))
    get_file_clipboard().set("copy", ["/work/a.txt", "/work/b.txt"])
    frame._wx_remote_run_action("paste", (), "/work/dest")
    pump(
        wx_app,
        lambda: not frame._wx_remote_state["busy"]
        and ("copy", "/work/a.txt", "/work/dest/a.txt") in backend.calls
        and ("copy", "/work/b.txt", "/work/dest/b.txt") in backend.calls,
    )
    assert len([call for call in backend.calls if call[0] == "copy"]) == 2


def test_ctrl_a_selects_all_rows(wx_app):
    backend = MockRemoteFilesBackend()
    backend.entries.update({"/work/folder": True})
    frame = browser(wx_app, backend, WxRemoteDirectoryModel("/work"))
    listing = frame._wx_remote_controls["listing"]
    event = wx.KeyEvent(wx.wxEVT_KEY_DOWN)
    event.SetKeyCode(ord("A"))
    event.SetControlDown(True)
    listing.ProcessEvent(event)
    assert all(listing.IsSelected(index) for index in range(listing.GetItemCount()))


def test_copy_path_uses_system_clipboard_adapter_without_backend(wx_app, monkeypatch):
    import hpc_gui.wx_remote_files_actions as actions

    backend = MockRemoteFilesBackend()
    frame = browser(wx_app, backend, WxRemoteDirectoryModel("/work"))
    written = []
    monkeypatch.setattr(
        actions, "set_system_clipboard_text",
        lambda _clipboard, _factory, value: written.append(value) or True,
    )

    frame._wx_remote_run_action("copy_path", ("/work",), "/")

    assert written == ["/work"]
    assert not any(call[0] in {"copy", "move"} for call in backend.calls)


def test_copy_path_preserves_multiple_selected_paths(wx_app, monkeypatch):
    import hpc_gui.wx_remote_files_actions as actions

    backend = MockRemoteFilesBackend()
    frame = browser(wx_app, backend, WxRemoteDirectoryModel("/work"))
    written = []
    monkeypatch.setattr(
        actions, "set_system_clipboard_text",
        lambda _clipboard, _factory, value: written.append(value) or True,
    )

    frame._wx_remote_run_action("copy_path", ("/work/a.txt", "/work/b.txt"), "/work")

    assert written == ["/work/a.txt\r\n/work/b.txt"]
    assert not backend.calls


def test_keyboard_cut_and_undo_restores_pending_clipboard(wx_app):
    backend = MockRemoteFilesBackend()
    frame = browser(wx_app, backend, WxRemoteDirectoryModel("/work"))
    listing = frame._wx_remote_controls["listing"]
    get_file_clipboard().set("copy", ["/work/a.txt"])
    row = next(index for index in range(listing.GetItemCount()) if listing.GetItemText(index) == "a.txt")
    listing.Select(row)

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

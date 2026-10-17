
pytest_plugins = ('support.test_wx_remote_file_actions_behavior_shared',)
from support.test_wx_remote_file_actions_behavior_shared import (
    MockRemoteFilesBackend,
    WxRemoteDirectoryModel,
    _DestinationDialog,
    _Dialog,
    _FileDialog,
    _browser,
    _pump,
    pytest,
    show_remote_files,
    threading,
    wx,
)

pytestmark = [pytest.mark.gui, pytest.mark.wx]

@pytest.mark.concurrency
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

def test_wx_remote_download_uses_selected_destination_dialog(wx_app, monkeypatch, tmp_path):
    backend = MockRemoteFilesBackend()
    frame = _browser(wx_app, backend)
    monkeypatch.setattr(wx, "DirDialog", lambda *_args, **_kwargs: _DestinationDialog(str(tmp_path)))
    frame._wx_remote_run_action("download", ("/work/a.txt",), "/work")
    _pump(wx_app, lambda: ("download", "/work/a.txt", str(tmp_path)) in backend.calls)

def test_wx_remote_delete_removes_selected_files_and_directory_only(wx_app, monkeypatch):
    backend = MockRemoteFilesBackend()
    backend.entries.update({"/work/selected-dir": True, "/work/selected-dir/nested.txt": False, "/work/keep.txt": False})
    frame = _browser(wx_app, backend, WxRemoteDirectoryModel("/work"))
    listing = frame._wx_remote_controls["listing"]
    monkeypatch.setattr(wx, "MessageBox", lambda *_args, **_kwargs: wx.YES)
    for name in ("a.txt", "selected-dir"):
        row = next(index for index in range(listing.GetItemCount()) if listing.GetItemText(index) == name)
        listing.Select(row)
    frame._wx_remote_run_action("delete", ("/work/a.txt", "/work/selected-dir"), "/work")
    _pump(wx_app, lambda: not frame._wx_remote_state["busy"])
    assert "/work/a.txt" not in backend.entries
    assert "/work/selected-dir" not in backend.entries
    assert "/work/selected-dir/nested.txt" not in backend.entries
    assert "/work/keep.txt" in backend.entries

def test_wx_remote_rename_updates_backend_and_visible_listing(wx_app, monkeypatch):
    backend = MockRemoteFilesBackend()
    frame = _browser(wx_app, backend, WxRemoteDirectoryModel("/work"))
    monkeypatch.setattr(wx, "TextEntryDialog", lambda *_args, **_kwargs: _Dialog("renamed.txt"))
    frame._wx_remote_run_action("rename", ("/work/a.txt",), "/work")
    _pump(wx_app, lambda: ("rename", "/work/a.txt", "/work/renamed.txt") in backend.calls)
    _pump(wx_app, lambda: not frame._wx_remote_state["busy"] and any(frame._wx_remote_controls["listing"].GetItemText(index) == "renamed.txt" for index in range(frame._wx_remote_controls["listing"].GetItemCount())))
    assert "/work/a.txt" not in backend.entries
    assert "/work/renamed.txt" in backend.entries

def test_wx_remote_rename_conflict_shows_error_and_preserves_source(wx_app, monkeypatch):
    backend = MockRemoteFilesBackend()
    errors = []
    frame = _browser(wx_app, backend, WxRemoteDirectoryModel("/work"))
    monkeypatch.setattr(wx, "TextEntryDialog", lambda *_args, **_kwargs: _Dialog("b.txt"))
    monkeypatch.setattr(wx, "MessageBox", lambda message, *_args, **_kwargs: errors.append(message) or wx.OK)
    frame._wx_remote_run_action("rename", ("/work/a.txt",), "/work")
    _pump(wx_app, lambda: not frame._wx_remote_state["busy"])
    assert errors
    assert "/work/a.txt" in backend.entries
    assert frame._wx_remote_controls["listing"].IsEnabled()

def test_remote_new_folder_uses_clicked_directory_target(wx_app, monkeypatch):
    backend = MockRemoteFilesBackend()
    frame = _browser(wx_app, backend)
    monkeypatch.setattr(wx, "TextEntryDialog", lambda *_args, **_kwargs: _Dialog("child"))
    frame._wx_remote_run_action("new_folder", ("/work",), "/work")
    _pump(wx_app, lambda: ("mkdir", "/work/child") in backend.calls)
    assert "/work/child" in backend.entries

def test_wx_remote_new_folder_rejects_invalid_name(wx_app, monkeypatch):
    backend = MockRemoteFilesBackend()
    errors = []
    frame = _browser(wx_app, backend, WxRemoteDirectoryModel("/work"))
    monkeypatch.setattr(wx, "TextEntryDialog", lambda *_args, **_kwargs: _Dialog("../bad"))
    monkeypatch.setattr(wx, "MessageBox", lambda message, *_args, **_kwargs: errors.append(message) or wx.OK)
    frame._wx_remote_run_action("new_folder", (), "/work")
    assert errors
    assert "/work/../bad" not in backend.entries
    assert frame._wx_remote_controls["listing"].IsEnabled()

def test_wx_remote_new_folder_failure_shows_error_and_recovers(wx_app, monkeypatch):
    backend = MockRemoteFilesBackend()
    errors = []

    def failing_operation(*_args, **_kwargs):
        raise OSError("mkdir failed")

    frame = _browser(wx_app, backend, WxRemoteDirectoryModel("/work"), failing_operation)
    monkeypatch.setattr(wx, "TextEntryDialog", lambda *_args, **_kwargs: _Dialog("child"))
    monkeypatch.setattr(wx, "MessageBox", lambda message, *_args, **_kwargs: errors.append(message) or wx.OK)
    frame._wx_remote_run_action("new_folder", (), "/work")
    _pump(wx_app, lambda: not frame._wx_remote_state["busy"])
    assert errors == ["mkdir failed"]
    assert frame._wx_remote_controls["listing"].IsEnabled()

def test_wx_remote_delete_confirmation_cancel_preserves_selection(wx_app, monkeypatch):
    backend = MockRemoteFilesBackend()
    frame = _browser(wx_app, backend, WxRemoteDirectoryModel("/work"))
    monkeypatch.setattr(wx, "MessageBox", lambda *_args, **_kwargs: wx.NO)
    frame._wx_remote_run_action("delete", ("/work/a.txt",), "/work")
    wx_app.ProcessPendingEvents()
    assert "/work/a.txt" in backend.entries
    assert not backend.calls
    assert frame._wx_remote_controls["listing"].IsEnabled()

def test_wx_remote_delete_failure_shows_error_and_recovers(wx_app, monkeypatch):
    errors = []

    def failing_operation(*_args, **_kwargs):
        raise OSError("delete failed")

    frame = _browser(wx_app, MockRemoteFilesBackend(), WxRemoteDirectoryModel("/work"), failing_operation)
    monkeypatch.setattr(wx, "MessageBox", lambda message, *_args, **_kwargs: errors.append(message) or wx.YES)
    frame._wx_remote_run_action("delete", ("/work/a.txt",), "/work")
    _pump(wx_app, lambda: not frame._wx_remote_state["busy"])
    assert errors[-1] == "delete failed"
    assert frame._wx_remote_controls["listing"].IsEnabled()

def test_wx_remote_move_preserves_multi_item_destinations(wx_app, monkeypatch):
    backend = MockRemoteFilesBackend()
    frame = _browser(wx_app, backend, WxRemoteDirectoryModel("/work"))
    monkeypatch.setattr(wx, "TextEntryDialog", lambda *_args, **_kwargs: _Dialog("/archive"))
    backend.entries["/archive"] = True
    frame._wx_remote_run_action("move", ("/work/a.txt", "/work/b.txt"), "/work")
    _pump(
        wx_app,
        lambda: not frame._wx_remote_state["busy"]
        and ("move", "/work/a.txt", "/archive/a.txt") in backend.calls
        and ("move", "/work/b.txt", "/archive/b.txt") in backend.calls,
    )
    assert "/archive/a.txt" in backend.entries
    assert "/archive/b.txt" in backend.entries
    assert "/work/a.txt" not in backend.entries
    assert "/work/b.txt" not in backend.entries

def test_wx_remote_ctrl_a_selects_all_rows(wx_app):
    backend = MockRemoteFilesBackend()
    backend.entries.update({"/work/folder": True})
    frame = _browser(wx_app, backend, WxRemoteDirectoryModel("/work"))
    listing = frame._wx_remote_controls["listing"]
    event = wx.KeyEvent(wx.wxEVT_KEY_DOWN)
    event.SetKeyCode(ord("A"))
    event.SetControlDown(True)
    listing.ProcessEvent(event)
    assert all(listing.IsSelected(index) for index in range(listing.GetItemCount()))

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

def test_wx_remote_new_file_and_chmod_reach_backend(wx_app, monkeypatch):
    class Backend(MockRemoteFilesBackend):
        def write_text(self, path, text):
            self._record("write_text", path, text)
            self.entries[path] = False

        def chmod(self, path, mode):
            self._record("chmod", path, mode)

        def operation(self, action, paths, destination=""):
            if action == "new_file":
                self.write_text(destination, "")
                return
            return super().operation(action, paths, destination)

    backend = Backend()
    show_remote_files(
        model=WxRemoteDirectoryModel("/work"), loader=backend.iterdir_entries,
        operation=backend.operation, chmod=backend.chmod,
    )
    frame = [window for window in wx.GetTopLevelWindows() if hasattr(window, "_wx_remote_controls")][-1]
    _pump(wx_app, lambda: frame._wx_remote_controls["listing"].GetItemCount() >= 1)
    monkeypatch.setattr(wx, "TextEntryDialog", lambda *_args, **_kwargs: _Dialog("test.txt"))
    frame._wx_remote_run_action("new_file", (), "/work")
    _pump(wx_app, lambda: ("write_text", "/work/test.txt", "") in backend.calls)
    assert backend.entries["/work/test.txt"] is False

    monkeypatch.setattr(wx, "TextEntryDialog", lambda *_args, **_kwargs: _Dialog("755"))
    frame._wx_remote_run_action("chmod", ("/work/test.txt",), "/work")
    _pump(wx_app, lambda: ("chmod", "/work/test.txt", 0o755) in backend.calls)

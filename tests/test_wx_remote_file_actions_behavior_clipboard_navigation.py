
pytest_plugins = ('support.test_wx_remote_file_actions_behavior_shared',)
from support.test_wx_remote_file_actions_behavior_shared import (
    MockRemoteFilesBackend,
    WxRemoteDirectoryModel,
    _browser,
    _pump,
    get_file_clipboard,
    pytest,
    read_clipboard_text,
    show_remote_files,
    wx,
)

pytestmark = [pytest.mark.gui, pytest.mark.wx]

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

def test_wx_remote_copy_path_uses_system_clipboard_without_backend(wx_app):
    backend = MockRemoteFilesBackend()
    frame = _browser(wx_app, backend, WxRemoteDirectoryModel("/work"))
    listing = frame._wx_remote_controls["listing"]
    listing.Select(0)
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
    listing.Select(0)
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

def test_wx_remote_navigation_sort_and_provider_filter_are_visible(wx_app):
    backend = MockRemoteFilesBackend()
    backend.entries.update({
        "/work/Folder A": True, "/work/Folder B": True,
        "/work/z.txt": False, "/work/run.log": False,
        "/work/sub": True, "/work/sub/child.txt": False,
    })
    show_remote_files(
        model=WxRemoteDirectoryModel("/work"), loader=backend.iterdir_entries,
        operation=backend.operation,
        provider_filters=[{"id": "logs", "labels": {"en": "Logs", "tr": "Günlükler"}, "suffixes": [".log"], "order": 100}],
    )
    frame = [window for window in wx.GetTopLevelWindows() if hasattr(window, "_wx_remote_controls")][-1]
    _pump(wx_app, lambda: frame._wx_remote_controls["listing"].GetItemCount() >= 1)
    controls = frame._wx_remote_controls
    listing = controls["listing"]
    for _ in range(2):
        event = wx.ListEvent(wx.wxEVT_LIST_COL_CLICK, listing.GetId())
        event.SetColumn(0)
        event.SetEventObject(listing)
        listing.GetEventHandler().ProcessEvent(event)
    names = [listing.GetItemText(index) for index in range(listing.GetItemCount())]
    assert names[:3] == ["sub", "Folder B", "Folder A"]
    assert set(names[3:]) == {"z.txt", "run.log", "a.txt", "b.txt"}

    tab = frame._wx_remote_tabs[0]
    filter_nb = tab["filter_notebook"]
    assert "Logs" in [filter_nb.GetPageText(index) for index in range(filter_nb.GetPageCount())]
    filter_nb.SetSelection(tab["filter_ids"].index("logs"))
    wx_app.ProcessPendingEvents()
    assert [listing.GetItemText(index) for index in range(listing.GetItemCount())] == ["run.log"]

    controls["navigate"]("/work/sub")
    controls["load"]()
    _pump(wx_app, lambda: controls["path"].GetValue() == "/work/sub")
    controls["btn_back"].ProcessEvent(wx.CommandEvent(wx.wxEVT_BUTTON, controls["btn_back"].GetId()))
    _pump(wx_app, lambda: controls["path"].GetValue() == "/work")
    controls["btn_forward"].ProcessEvent(wx.CommandEvent(wx.wxEVT_BUTTON, controls["btn_forward"].GetId()))
    _pump(wx_app, lambda: controls["path"].GetValue() == "/work/sub")

def test_wx_remote_favorite_selected_file_targets_file_path(wx_app):
    class Store:
        def __init__(self):
            self.items = []

        def favorites(self):
            return list(self.items)

        def toggle_favorite(self, path, kind):
            self.items.append({"path": path, "kind": kind, "label": path.rsplit("/", 1)[-1]})

    store = Store()
    backend = MockRemoteFilesBackend()
    show_remote_files(
        model=WxRemoteDirectoryModel("/work"), loader=backend.iterdir_entries,
        operation=backend.operation, navigation_store=store,
    )
    frame = [window for window in wx.GetTopLevelWindows() if hasattr(window, "_wx_remote_controls")][-1]
    _pump(wx_app, lambda: frame._wx_remote_controls["listing"].GetItemCount() >= 1)
    frame._wx_remote_run_action("favorite", ("/work/a.txt",), "/work")
    assert store.items == [{"path": "/work/a.txt", "kind": "file", "label": "a.txt"}]

def test_wx_remote_submit_slurm_uses_selected_remote_path(wx_app, monkeypatch):
    backend = MockRemoteFilesBackend()
    submitted = []
    messages = []
    frame = show_remote_files(
        model=WxRemoteDirectoryModel("/work"), loader=backend.iterdir_entries,
        operation=backend.operation,
        submit_slurm=lambda path: submitted.append(path) or "Submitted batch job 77",
    )
    frame = [window for window in wx.GetTopLevelWindows() if hasattr(window, "_wx_remote_controls")][-1]
    _pump(wx_app, lambda: frame._wx_remote_controls["listing"].GetItemCount() >= 1)
    monkeypatch.setattr(wx, "MessageBox", lambda message, *_args, **_kwargs: messages.append(message) or wx.OK)
    frame._wx_remote_run_action("submit_slurm", ("/work/job.sbatch",), "/work")
    _pump(wx_app, lambda: not frame._wx_remote_state["busy"])
    assert submitted == ["/work/job.sbatch"]
    assert messages == ["Submitted batch job 77"]

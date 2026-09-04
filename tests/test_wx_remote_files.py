from hpc_gui.wx_remote_files import RemoteEntry, WxRemoteDirectoryModel


def test_large_batched_listing_stale_refresh_and_cache():
    model = WxRemoteDirectoryModel("/home/user", cache_ttl=60)
    entries = tuple(RemoteEntry(f"/home/user/{i}") for i in range(405))
    calls = []
    def loader(path):
        calls.append(path)
        return entries
    assert len(model.batched(entries)) == 3
    assert model.list_entries(loader) == entries and model.list_entries(loader) == entries
    assert len(calls) == 1
    first = model.navigate("/one")
    second = model.navigate("/two")
    assert not model.is_current(first) and model.is_current(second)


def test_remote_clipboard_undo_permissions_and_middle_click():
    model = WxRemoteDirectoryModel()
    assert model.clipboard_payload(["/a/space name", "/b"]).startswith("/a/")
    assert model.operation("undo", ("/a",)).kind == "undo"
    request = model.permission_request("/a", owner=7, group=5, others=0, special=1)
    assert request.special == 1 and not request.recursive
    try:
        model.permission_request("/a", owner=7, group=7, others=7, recursive=True)
    except ValueError:
        pass
    else:
        raise AssertionError("recursive chmod must stay disabled")
    assert model.middle_click("/folder") == 1
    assert model.context_action("rename", ["/a"], "/b").kind == "rename"


def test_remote_model_has_no_toolkit_import():
    source = open("src/hpc_gui/wx_remote_files.py", encoding="utf-8").read()
    assert "PySide6" not in source and "import wx" not in source


def test_remote_view_runs_operations_off_the_wx_thread():
    source = open("src/hpc_gui/wx_remote_files_view.py", encoding="utf-8").read()
    assert "Thread(target=worker" in source
    assert 't("dirs.delete_confirm")' in source
    assert "safe_call_after(operation_done" in source
    assert '"open", "edit", "edit_new_window", "run_shell", "download"' in source
    assert "open_editor_new_window=None" in source
    assert "read_text=None" in source and "safe_call_after(done, read_text(remote_path), None)" in source
    assert "navigate(requested_path_text)" in source and "path.SetValue(tstate[\"path\"])" in source
    assert "PurePosixPath(selected[0]).parent / new_name" in source and "operation(action, operation_paths, destination)" in source
    assert 'action in {"rename", "copy", "move"}' in source and "dirs.destination" in source
    assert 'action == "download"' in source and "wx.DirDialog" in source
    assert 'action == "upload"' in source and "wx.FileDialog" in source
    assert "EVT_KEY_DOWN" in source and "WXK_BACK" in source and "WXK_F2" in source
    assert 'action == "new_folder"' in source and "wx.TextEntryDialog" in source

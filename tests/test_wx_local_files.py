from pathlib import Path

from hpc_gui.wx_local_files import LocalBrowserModel, file_url_payload


def test_local_browser_paths_sort_tabs_and_context(tmp_path: Path):
    (tmp_path / "á file.txt").write_text("x", encoding="utf-8")
    (tmp_path / "folder").mkdir()
    model = LocalBrowserModel(tmp_path)
    assert {entry.path.name for entry in model.list_entries()} == {"á file.txt", "folder"}
    model.sort("size")
    tab = model.new_tab(tmp_path / "folder")
    assert tab == 1 and model.current_path.name == "folder"
    assert "new_tab" in model.context_actions(True)
    opened = []
    assert model.activate(tmp_path / "á file.txt", open_editor=opened.append) == "edit"
    assert opened == [str((tmp_path / "á file.txt").resolve())]
    assert model.file_action("rename", tmp_path / "x")[:2] == ("rename", str(tmp_path / "x"))
    (tmp_path / "folder" / "child.txt").write_text("x", encoding="utf-8")
    renamed = model.rename(tmp_path / "folder" / "child.txt", "renamed.txt")
    assert renamed.name == "renamed.txt"
    assert model.delete([renamed]) == (renamed,)
    try:
        model.delete([tmp_path])
    except ValueError:
        pass
    else:
        raise AssertionError("current directory must not be deletable")
    created = model.new_folder("new-folder")
    assert created.is_dir()
    model.close_tab()
    assert model.current_path == tmp_path.resolve()


def test_file_url_clipboard_payload_preserves_spaces_and_unicode(tmp_path: Path):
    path = tmp_path / "space ü.txt"
    payload = file_url_payload([path])
    assert payload.startswith("file:///") and "%20" in payload and "%C3%BC" in payload


def test_local_clipboard_copy_and_move_paste(tmp_path: Path):
    source = tmp_path / "source.txt"
    source.write_text("data", encoding="utf-8")
    target_dir = tmp_path / "target"
    target_dir.mkdir()
    model = LocalBrowserModel(target_dir)
    model.copy([source])
    assert model.paste() == (target_dir / source.name,)
    moved = tmp_path / "moved.txt"
    moved.write_text("data", encoding="utf-8")
    model.copy([moved], move=True)
    assert model.paste() == (target_dir / moved.name,) and not moved.exists()


def test_local_browser_model_has_no_toolkit_import():
    source = open("src/hpc_gui/wx_local_files.py", encoding="utf-8").read()
    assert "from PySide6" not in source


def test_local_context_actions_include_safe_navigation_actions():
    actions = LocalBrowserModel.context_actions(True)
    assert "copy_path" in actions and "refresh" in actions and "new_tab" in actions


def test_local_view_exposes_keyboard_and_context_actions():
    source = open("src/hpc_gui/wx_local_files.py", encoding="utf-8").read()
    assert "EVT_LIST_ITEM_ACTIVATED" in source
    assert "EVT_CONTEXT_MENU" in source and "open_editor" in source
    assert 'actions = (model.context_actions(entry.is_dir)' in source and '"new_folder", "refresh"' in source
    assert "EVT_KEY_DOWN" in source and "WXK_F2" in source and "WXK_DELETE" in source
    assert "model.copy" in source and "model.paste" in source and "ControlDown" in source
    assert "WXK_BACK" in source and "GetItemCount()" in source

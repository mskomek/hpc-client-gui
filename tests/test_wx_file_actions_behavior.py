import time
import os
import subprocess
from pathlib import Path

import pytest

wx = pytest.importorskip("wx")

from hpc_gui import wx_local_files
from hpc_gui.wx_local_files import show_local_files
from hpc_gui.core.i18n import load_language


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
    app = wx.App(False)
    yield app
    for window in wx.GetTopLevelWindows():
        if window:
            window.Destroy()
    app.ProcessPendingEvents()
    app.Destroy()


def _browser(wx_app, path, **callbacks):
    show_local_files(path=path, **callbacks)
    frame = [window for window in wx.GetTopLevelWindows() if hasattr(window, "_wx_local_controls")][-1]
    wx_app.ProcessPendingEvents()
    return frame


def test_local_double_click_routes_file_to_editor_and_folder_to_visible_navigation(wx_app, tmp_path: Path):
    (tmp_path / "job.slurm").write_text("#!/bin/bash\n", encoding="utf-8")
    (tmp_path / "results").mkdir()
    opened = []
    frame = _browser(wx_app, tmp_path, open_editor=opened.append)
    listing = frame._wx_local_controls["listing"]
    file_index = next(i for i in range(listing.GetItemCount()) if listing.GetItemText(i) == "job.slurm")
    event = wx.ListEvent(wx.wxEVT_LIST_ITEM_ACTIVATED, listing.GetId())
    event.SetIndex(file_index)
    listing.ProcessEvent(event)
    assert opened == [str((tmp_path / "job.slurm").resolve())]
    folder_index = next(i for i in range(listing.GetItemCount()) if listing.GetItemText(i) == "results")
    event.SetIndex(folder_index)
    listing.ProcessEvent(event)
    assert frame._wx_local_state["context_target"] is None
    _pump(wx_app, lambda: frame._wx_local_controls["listing"].GetItemCount() == 0)


def test_local_context_event_targets_unselected_row_without_dropping_target(wx_app, tmp_path: Path):
    for name in ("a.txt", "b.txt"):
        (tmp_path / name).write_text(name, encoding="utf-8")
    frame = _browser(wx_app, tmp_path)
    listing = frame._wx_local_controls["listing"]
    listing.Select(0)
    seen = []
    listing.PopupMenu = lambda menu: seen.extend(item.GetItemLabelText() for item in menu.GetMenuItems())
    index = 1
    point = listing.ClientToScreen(wx.Point(5, listing.GetItemRect(index).y + 2))
    event = wx.ContextMenuEvent(wx.wxEVT_CONTEXT_MENU, listing.GetId())
    event.SetPosition(point)
    listing.ProcessEvent(event)
    assert listing.IsSelected(index)
    assert "Edit" in seen


def test_local_delete_key_runs_async_and_refreshes_visible_rows(wx_app, tmp_path: Path, monkeypatch):
    target = tmp_path / "remove.txt"
    target.write_text("x", encoding="utf-8")
    frame = _browser(wx_app, tmp_path)
    listing = frame._wx_local_controls["listing"]
    listing.Select(0)
    monkeypatch.setattr(wx, "MessageBox", lambda *_args, **_kwargs: wx.YES)
    event = wx.KeyEvent(wx.wxEVT_KEY_DOWN)
    event.SetKeyCode(wx.WXK_DELETE)
    listing.ProcessEvent(event)
    _pump(wx_app, lambda: not target.exists() and listing.GetItemCount() == 0)


def test_wx_local_f5_refreshes_without_a_selection(wx_app, tmp_path: Path):
    frame = _browser(wx_app, tmp_path)
    listing = frame._wx_local_controls["listing"]
    assert listing.GetItemCount() == 0
    (tmp_path / "new.txt").write_text("x", encoding="utf-8")
    event = wx.KeyEvent(wx.wxEVT_KEY_DOWN)
    event.SetKeyCode(wx.WXK_F5)
    listing.ProcessEvent(event)
    _pump(wx_app, lambda: listing.GetItemCount() == 1)
    assert listing.GetItemText(0) == "new.txt"


def test_wx_local_delete_removes_selected_files_and_directories_only(wx_app, tmp_path: Path, monkeypatch):
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    (tmp_path / "b.txt").write_text("b", encoding="utf-8")
    selected_dir = tmp_path / "selected-dir"
    selected_dir.mkdir()
    (selected_dir / "nested.txt").write_text("nested", encoding="utf-8")
    untouched = tmp_path / "untouched.txt"
    untouched.write_text("keep", encoding="utf-8")
    frame = _browser(wx_app, tmp_path)
    listing = frame._wx_local_controls["listing"]
    monkeypatch.setattr(wx, "MessageBox", lambda *_args, **_kwargs: wx.YES)
    for name in ("a.txt", "selected-dir"):
        row = next(index for index in range(listing.GetItemCount()) if listing.GetItemText(index) == name)
        listing.Select(row)
    frame._wx_local_run_action("delete")
    _pump(wx_app, lambda: not frame._wx_local_state["mutation_in_flight"])
    assert not (tmp_path / "a.txt").exists()
    assert not selected_dir.exists()
    assert (tmp_path / "b.txt").exists()
    assert untouched.exists()


def test_local_directory_context_creates_folder_under_clicked_directory(wx_app, tmp_path: Path, monkeypatch):
    folder = tmp_path / "folder"
    folder.mkdir()
    frame = _browser(wx_app, tmp_path)
    listing = frame._wx_local_controls["listing"]
    index = 0
    listing.Select(index)
    monkeypatch.setattr(wx, "TextEntryDialog", lambda *_args, **_kwargs: _Dialog(wx, "child"))
    frame._wx_local_run_action("new_folder")
    _pump(wx_app, lambda: (folder / "child").is_dir())


class _Dialog:
    def __init__(self, _wx, value):
        self.value = value

    def ShowModal(self):
        return wx.ID_OK

    def GetValue(self):
        return self.value

    def Destroy(self):
        pass


@pytest.mark.parametrize("is_dir", [False, True])
def test_reveal_file_manager_windows_uses_parent_or_directory(monkeypatch, tmp_path: Path, is_dir):
    target = tmp_path / ("folder" if is_dir else "file.txt")
    target.mkdir() if is_dir else target.write_text("x", encoding="utf-8")
    opened = []
    monkeypatch.setattr(os, "startfile", opened.append, raising=False)
    monkeypatch.setattr(wx_local_files.sys, "platform", "win32")
    wx_local_files.reveal_in_file_manager(target)
    assert opened == [str(target if is_dir else target.parent)]


@pytest.mark.parametrize("is_dir", [False, True])
def test_reveal_file_manager_macos_uses_finder_semantics(monkeypatch, tmp_path: Path, is_dir):
    target = tmp_path / ("folder" if is_dir else "file.txt")
    target.mkdir() if is_dir else target.write_text("x", encoding="utf-8")
    calls = []
    monkeypatch.delattr(os, "startfile", raising=False)
    monkeypatch.setattr(wx_local_files.sys, "platform", "darwin")
    monkeypatch.setattr(subprocess, "Popen", lambda args: calls.append(args))
    wx_local_files.reveal_in_file_manager(target)
    assert calls == [["open", str(target)] if is_dir else ["open", "-R", str(target)]]


@pytest.mark.parametrize("is_dir", [False, True])
def test_reveal_file_manager_linux_opens_parent_or_directory(monkeypatch, tmp_path: Path, is_dir):
    target = tmp_path / ("folder" if is_dir else "file.txt")
    target.mkdir() if is_dir else target.write_text("x", encoding="utf-8")
    calls = []
    monkeypatch.delattr(os, "startfile", raising=False)
    monkeypatch.setattr(wx_local_files.sys, "platform", "linux")
    monkeypatch.setattr(subprocess, "Popen", lambda args: calls.append(args))
    wx_local_files.reveal_in_file_manager(target)
    assert calls == [["xdg-open", str(target if is_dir else target.parent)]]

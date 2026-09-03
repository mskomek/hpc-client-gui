import time
from pathlib import Path

import pytest

wx = pytest.importorskip("wx")

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
    assert frame._wx_local_controls["listing"].GetItemCount() == 0


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
    _pump(wx_app, lambda: not target.exists())
    assert listing.GetItemCount() == 0


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

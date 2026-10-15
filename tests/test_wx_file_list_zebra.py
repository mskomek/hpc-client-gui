"""Visible alternating row colors in native local and remote file lists."""

from __future__ import annotations

import time

import pytest

wx = pytest.importorskip("wx")

from hpc_gui.core.i18n import load_language
from hpc_gui.wx_local_files import show_local_files
from hpc_gui.wx_file_type_icons import file_type_icon_index
from hpc_gui.wx_remote_files import WxRemoteDirectoryModel
from hpc_gui.wx_remote_files_view import show_remote_files
from mock_hpc_files import MockRemoteFilesBackend


@pytest.fixture
def wx_app():
    load_language("en")
    created_app = wx.App.Get() is None
    app = wx.App.Get() or wx.App(False)
    yield app
    for window in wx.GetTopLevelWindows():
        if window:
            window.Destroy()
    app.ProcessPendingEvents()
    wx.YieldIfNeeded()
    app.ProcessPendingEvents()
    if created_app:
        app.Destroy()


def _wait_for_rows(app, listing, count):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline and listing.GetItemCount() < count:
        app.ProcessPendingEvents()
        wx.MilliSleep(5)
    app.ProcessPendingEvents()
    assert listing.GetItemCount() >= count


def _assert_zebra_rows(listing):
    colors = [listing.GetItemBackgroundColour(index) for index in range(3)]
    assert colors[0] != colors[1]
    assert colors[0] == colors[2]


@pytest.mark.gui
@pytest.mark.wx
def test_local_file_list_uses_alternating_row_colors(wx_app, tmp_path):
    for name in ("a.py", "b.txt", "c.png"):
        (tmp_path / name).write_text(name, encoding="utf-8")
    (tmp_path / "d-folder").mkdir()

    show_local_files(path=tmp_path)
    frame = next(window for window in wx.GetTopLevelWindows() if hasattr(window, "_wx_local_controls"))
    listing = frame._wx_local_controls["listing"]
    _wait_for_rows(wx_app, listing, 3)

    _assert_zebra_rows(listing)
    assert listing.GetItem(0).GetImage() == file_type_icon_index("a.py", False)
    assert listing.GetItem(1).GetImage() == file_type_icon_index("b.txt", False)
    assert listing.GetItem(2).GetImage() == file_type_icon_index("c.png", False)
    assert listing.GetItem(3).GetImage() == file_type_icon_index("d-folder", True)


@pytest.mark.gui
@pytest.mark.wx
def test_remote_file_list_uses_alternating_row_colors(wx_app):
    backend = MockRemoteFilesBackend()
    backend.entries.update({"/work/c.py": False, "/work/d.png": False})

    show_remote_files(
        model=WxRemoteDirectoryModel("/work"),
        loader=backend.iterdir_entries,
        operation=backend.operation,
    )
    frame = next(window for window in wx.GetTopLevelWindows() if hasattr(window, "_wx_remote_controls"))
    listing = frame._wx_remote_controls["listing"]
    _wait_for_rows(wx_app, listing, 3)

    _assert_zebra_rows(listing)
    for name in ("a.txt", "b.txt", "c.py", "d.png"):
        index = listing.FindItem(-1, name)
        assert index >= 0
        assert listing.GetItem(index).GetImage() == file_type_icon_index(name, False)

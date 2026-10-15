"""Visible alternating row colors in native local and remote file lists."""

from __future__ import annotations

import time

import pytest

wx = pytest.importorskip("wx")

from hpc_gui.core.i18n import load_language
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
def test_remote_file_list_uses_alternating_row_colors(wx_app):
    backend = MockRemoteFilesBackend()
    backend.entries.update({"/work/c.txt": False})

    show_remote_files(
        model=WxRemoteDirectoryModel("/work"),
        loader=backend.iterdir_entries,
        operation=backend.operation,
    )
    frame = next(window for window in wx.GetTopLevelWindows() if hasattr(window, "_wx_remote_controls"))
    listing = frame._wx_remote_controls["listing"]
    _wait_for_rows(wx_app, listing, 3)

    _assert_zebra_rows(listing)

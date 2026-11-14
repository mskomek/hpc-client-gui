"""Header sorting behavior for the wx local Files pane."""

import time
from pathlib import Path

import pytest

wx = pytest.importorskip("wx")
pytestmark = [pytest.mark.gui, pytest.mark.wx]

from hpc_gui.wx_local_files import show_local_files
from hpc_gui.wx_remote_files import WxRemoteDirectoryModel
from hpc_gui.wx_remote_files_view import show_remote_files
from mock_hpc_files import MockRemoteFilesBackend


def _pump(app, predicate, timeout=3):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.ProcessPendingEvents()
        if predicate():
            return
        wx.MilliSleep(5)
    assert predicate()


def test_size_header_sorts_both_directions_and_pins_parent(tmp_path: Path):
    app = wx.App.Get() or wx.App(False)
    (tmp_path / "large.txt").write_bytes(b"x" * 20)
    (tmp_path / "small.txt").write_bytes(b"x")
    show_local_files(path=tmp_path)
    frame = next(w for w in wx.GetTopLevelWindows() if hasattr(w, "_wx_local_controls"))
    try:
        listing = frame._wx_local_controls["listing"]
        _pump(app, lambda: listing.GetItemCount() == 3)
        for expected in (("small.txt", "large.txt"), ("large.txt", "small.txt")):
            event = wx.ListEvent(wx.wxEVT_LIST_COL_CLICK, listing.GetId())
            event.SetColumn(1)
            listing.GetEventHandler().ProcessEvent(event)
            wx.YieldIfNeeded()
            assert listing.GetItemText(0) == ".."
            assert tuple(listing.GetItemText(i) for i in range(1, 3)) == expected
    finally:
        frame.Destroy()
        wx.YieldIfNeeded()
        if app is not None:
            app.Destroy()


def test_remote_name_header_keeps_parent_row_first():
    app = wx.App.Get() or wx.App(False)
    backend = MockRemoteFilesBackend()
    show_remote_files(
        model=WxRemoteDirectoryModel("/work"),
        loader=backend.iterdir_entries,
        operation=backend.operation,
    )
    frame = next(w for w in wx.GetTopLevelWindows() if hasattr(w, "_wx_remote_controls"))
    try:
        listing = frame._wx_remote_controls["listing"]
        _pump(app, lambda: listing.GetItemCount() >= 3)
        for expected in (("..", "a.txt", "b.txt"), ("..", "b.txt", "a.txt")):
            event = wx.ListEvent(wx.wxEVT_LIST_COL_CLICK, listing.GetId())
            event.SetColumn(0)
            listing.GetEventHandler().ProcessEvent(event)
            wx.YieldIfNeeded()
            assert tuple(listing.GetItemText(i) for i in range(3)) == expected
    finally:
        frame.Destroy()
        wx.YieldIfNeeded()
        if app is not None:
            app.Destroy()

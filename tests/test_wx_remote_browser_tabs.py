"""wx browser tab lifecycle contracts grouped by local or remote surface."""

from __future__ import annotations

import threading


import pytest

wx = pytest.importorskip("wx")
pytestmark = [pytest.mark.gui, pytest.mark.wx]
pytest_plugins = ("wx_file_browser_tabs_support",)

from wx_file_browser_tabs_support import _pump, _remote
from hpc_gui.wx_remote_files import RemoteEntry, WxRemoteDirectoryModel
from hpc_gui.wx_remote_files_view import show_remote_files
from mock_hpc_files import MockRemoteFilesBackend


def test_wx_remote_new_tab_creates_visible_second_tab(wx_app):
    backend = MockRemoteFilesBackend()
    frame = _remote(wx_app, backend, "/work")
    nb = frame._wx_remote_notebook
    assert nb.GetPageCount() == 1
    listing = frame._wx_remote_controls["listing"]
    _pump(wx_app, lambda: listing.GetItemCount() >= 1)
    backend.entries["/work/subdir"] = True
    frame._wx_remote_model.invalidate()
    frame._wx_remote_run_action("new_tab", ("/work/subdir",), "/work")
    _pump(wx_app, lambda: nb.GetPageCount() == 2)
    assert nb.GetSelection() == 1


def test_wx_remote_new_tab_preserves_original_path(wx_app):
    backend = MockRemoteFilesBackend()
    frame = _remote(wx_app, backend, "/work")
    nb = frame._wx_remote_notebook
    frame._wx_remote_run_action("new_tab", ("/work",), "/work")
    _pump(wx_app, lambda: nb.GetPageCount() == 2)
    assert frame._wx_remote_tabs[0]["path"] == "/work"


def test_wx_remote_switch_tabs_restores_correct_remote_path(wx_app):
    backend = MockRemoteFilesBackend()
    backend.entries["/scratch"] = True
    backend.entries["/scratch/file.txt"] = False
    frame = _remote(wx_app, backend, "/work")
    nb = frame._wx_remote_notebook
    frame._wx_remote_run_action("new_tab", ("/scratch",), "/scratch")
    _pump(wx_app, lambda: nb.GetPageCount() == 2)
    nb.SetSelection(0)
    _pump(wx_app, lambda: frame._wx_remote_controls["path"].GetValue() == "/work")
    assert frame._wx_remote_controls["path"].GetValue() == "/work"
    nb.SetSelection(1)
    _pump(wx_app, lambda: frame._wx_remote_controls["path"].GetValue() == "/scratch")


def test_wx_remote_closed_tab_ignores_late_listing_completion(wx_app):
    started = threading.Event()
    release = threading.Event()

    def loader(path):
        if path == "/work":
            started.set()
            release.wait(2)
            return (RemoteEntry("/work/old.txt"),)
        return (RemoteEntry("/scratch/new.txt"),)

    frame = (
        show_remote_files(
            model=WxRemoteDirectoryModel("/work"), loader=loader, operation=lambda *_a: None
        )
        or None
    )
    frame = [w for w in wx.GetTopLevelWindows() if hasattr(w, "_wx_remote_controls")][-1]
    nb = frame._wx_remote_notebook
    assert started.wait(2)
    # create second tab via production New Tab to allow closing first
    frame._wx_remote_run_action("new_tab", ("/scratch",), "/scratch")
    _pump(wx_app, lambda: nb.GetPageCount() == 2)
    # close original tab (0) via user-driven close
    orig_popup = nb.PopupMenu

    def capture(menu):
        for item in menu.GetMenuItems():
            if item.GetItemLabelText() == "Close":
                # need to target tab 0
                orig_hit = nb.HitTest
                nb.HitTest = lambda pt: (0, 0)
                nb.ProcessEvent(wx.CommandEvent(wx.wxEVT_MENU, item.GetId()))
                nb.HitTest = orig_hit
                break

    nb.PopupMenu = capture
    event = wx.ContextMenuEvent(wx.wxEVT_CONTEXT_MENU, nb.GetId())
    event.SetPosition(nb.ClientToScreen(wx.Point(5, 5)))
    nb.ProcessEvent(event)
    nb.PopupMenu = orig_popup
    release.set()
    wx_app.ProcessPendingEvents()
    wx.MilliSleep(50)
    assert frame._wx_remote_tabs[0]["path"] == "/scratch"


def test_wx_remote_stale_listing_cannot_cross_tab_boundary(wx_app):
    started = threading.Event()
    release = threading.Event()
    finished = threading.Event()

    def loader(path):
        if path == "/work":
            started.set()
            release.wait(2)
            finished.set()
            return (RemoteEntry("/work/old.txt"),)
        return (RemoteEntry("/scratch/new.txt"),)

    show_remote_files(
        model=WxRemoteDirectoryModel("/work"), loader=loader, operation=lambda *_a: None
    )
    frame = [w for w in wx.GetTopLevelWindows() if hasattr(w, "_wx_remote_controls")][-1]
    nb = frame._wx_remote_notebook
    assert started.wait(2)
    frame._wx_remote_run_action("new_tab", ("/scratch",), "/scratch")
    _pump(wx_app, lambda: nb.GetPageCount() == 2)
    # wait for second tab to load new.txt
    active = frame._wx_remote_controls["listing"]
    _pump(
        wx_app,
        lambda: any(active.GetItemText(i) == "new.txt" for i in range(active.GetItemCount())),
    )
    release.set()
    assert finished.wait(2)
    wx_app.ProcessPendingEvents()
    assert any(active.GetItemText(i) == "new.txt" for i in range(active.GetItemCount()))
    assert not any(active.GetItemText(i) == "old.txt" for i in range(active.GetItemCount()))


def test_wx_remote_tab_switch_does_not_create_new_backend_session(wx_app):
    backend = MockRemoteFilesBackend()
    frame = _remote(wx_app, backend, "/work")
    before = len(backend.calls) if hasattr(backend, "calls") else 0
    frame._wx_remote_run_action("new_tab", ("/work",), "/work")
    _pump(wx_app, lambda: frame._wx_remote_notebook.GetPageCount() == 2)
    frame._wx_remote_notebook.SetSelection(0)
    wx_app.ProcessPendingEvents()
    assert len(backend.calls) == before


def test_wx_remote_listing_worker_uses_captured_tab_path(wx_app):
    # regression for P0-1: worker must use captured path, not current_path
    calls = []
    started_work = threading.Event()
    release_work = threading.Event()
    finished_work = threading.Event()

    def loader(path):
        calls.append(path)
        if path == "/work":
            started_work.set()
            release_work.wait(2)
            finished_work.set()
            return (RemoteEntry("/work/work.txt"),)
        return (RemoteEntry("/scratch/scratch.txt"),)

    show_remote_files(
        model=WxRemoteDirectoryModel("/work"), loader=loader, operation=lambda *_a: None
    )
    frame = [w for w in wx.GetTopLevelWindows() if hasattr(w, "_wx_remote_controls")][-1]
    nb = frame._wx_remote_notebook
    assert started_work.wait(2)
    # open second tab via production New Tab
    frame._wx_remote_run_action("new_tab", ("/scratch",), "/scratch")
    _pump(wx_app, lambda: nb.GetPageCount() == 2)
    active = frame._wx_remote_controls["listing"]
    _pump(
        wx_app,
        lambda: any(active.GetItemText(i) == "scratch.txt" for i in range(active.GetItemCount())),
    )
    release_work.set()
    assert finished_work.wait(2)
    wx_app.ProcessPendingEvents()
    assert calls[0] == "/work"
    assert calls[1] == "/scratch"
    # Tab A visible rows belong only to /work when switched back
    nb.SetSelection(0)
    _pump(
        wx_app,
        lambda: any(
            frame._wx_remote_controls["listing"].GetItemText(i) == "work.txt"
            for i in range(frame._wx_remote_controls["listing"].GetItemCount())
        ),
    )
    assert any(
        frame._wx_remote_controls["listing"].GetItemText(i) == "work.txt"
        for i in range(frame._wx_remote_controls["listing"].GetItemCount())
    )
    assert not any(
        frame._wx_remote_controls["listing"].GetItemText(i) == "scratch.txt"
        for i in range(frame._wx_remote_controls["listing"].GetItemCount())
    )
    nb.SetSelection(1)
    assert any(
        frame._wx_remote_controls["listing"].GetItemText(i) == "scratch.txt"
        for i in range(frame._wx_remote_controls["listing"].GetItemCount())
    )
    assert not any(
        frame._wx_remote_controls["listing"].GetItemText(i) == "work.txt"
        for i in range(frame._wx_remote_controls["listing"].GetItemCount())
    )


def test_wx_remote_middle_click_directory_opens_tab(wx_app):
    backend = MockRemoteFilesBackend()
    backend.entries["/work/folder"] = True
    frame = _remote(wx_app, backend, "/work")
    nb = frame._wx_remote_notebook
    listing = frame._wx_remote_controls["listing"]
    _pump(wx_app, lambda: listing.GetItemCount() >= 1)
    idx = next(
        (i for i in range(listing.GetItemCount()) if listing.GetItemText(i) == "folder"), None
    )
    assert idx is not None
    rect = listing.GetItemRect(idx)
    event = wx.MouseEvent(wx.wxEVT_MIDDLE_DOWN)
    event.SetPosition(wx.Point(rect.x + 2, rect.y + 2))
    listing.ProcessEvent(event)
    _pump(wx_app, lambda: nb.GetPageCount() == 2)


def test_wx_remote_middle_click_file_noop(wx_app):
    backend = MockRemoteFilesBackend()
    frame = _remote(wx_app, backend, "/work")
    nb = frame._wx_remote_notebook
    listing = frame._wx_remote_controls["listing"]
    _pump(wx_app, lambda: listing.GetItemCount() >= 1)
    idx = next(i for i in range(listing.GetItemCount()) if listing.GetItemText(i) == "a.txt")
    rect = listing.GetItemRect(idx)
    event = wx.MouseEvent(wx.wxEVT_MIDDLE_DOWN)
    event.SetPosition(wx.Point(rect.x + 2, rect.y + 2))
    listing.ProcessEvent(event)
    wx_app.ProcessPendingEvents()
    assert nb.GetPageCount() == 1


def test_wx_remote_middle_click_background_noop(wx_app):
    backend = MockRemoteFilesBackend()
    frame = _remote(wx_app, backend, "/work")
    nb = frame._wx_remote_notebook
    listing = frame._wx_remote_controls["listing"]
    size = listing.GetSize()
    event = wx.MouseEvent(wx.wxEVT_MIDDLE_DOWN)
    event.SetPosition(wx.Point(5, max(5, size.height - 5)))
    listing.ProcessEvent(event)
    wx_app.ProcessPendingEvents()
    assert nb.GetPageCount() == 1


def test_wx_remote_user_close_tab_closes_visible_tab(wx_app):
    backend = MockRemoteFilesBackend()
    frame = _remote(wx_app, backend, "/work")
    nb = frame._wx_remote_notebook
    frame._wx_remote_run_action("new_tab", ("/work",), "/work")
    _pump(wx_app, lambda: nb.GetPageCount() == 2)
    orig_popup = nb.PopupMenu

    def capture(menu):
        for item in menu.GetMenuItems():
            if item.GetItemLabelText() == "Close":
                nb.ProcessEvent(wx.CommandEvent(wx.wxEVT_MENU, item.GetId()))
                break

    nb.PopupMenu = capture
    event = wx.ContextMenuEvent(wx.wxEVT_CONTEXT_MENU, nb.GetId())
    event.SetPosition(nb.ClientToScreen(wx.Point(10, 10)))
    nb.ProcessEvent(event)
    nb.PopupMenu = orig_popup
    _pump(wx_app, lambda: nb.GetPageCount() == 1)


def test_wx_remote_user_cannot_close_last_tab(wx_app):
    backend = MockRemoteFilesBackend()
    frame = _remote(wx_app, backend, "/work")
    nb = frame._wx_remote_notebook
    assert nb.GetPageCount() == 1
    orig_popup = nb.PopupMenu
    captured = []

    def capture(menu):
        for item in menu.GetMenuItems():
            if item.GetItemLabelText() == "Close":
                captured.append(item.IsEnabled())
                break

    nb.PopupMenu = capture
    event = wx.ContextMenuEvent(wx.wxEVT_CONTEXT_MENU, nb.GetId())
    event.SetPosition(nb.ClientToScreen(wx.Point(10, 10)))
    nb.ProcessEvent(event)
    nb.PopupMenu = orig_popup
    assert captured[0] is False


def test_wx_remote_user_close_inflight_tab_ignores_completion(wx_app):
    started = threading.Event()
    release = threading.Event()

    def loader(path):
        if path == "/work":
            started.set()
            release.wait(2)
            return (RemoteEntry("/work/late.txt"),)
        return (RemoteEntry("/scratch/ok.txt"),)

    show_remote_files(
        model=WxRemoteDirectoryModel("/work"), loader=loader, operation=lambda *_a: None
    )
    frame = [w for w in wx.GetTopLevelWindows() if hasattr(w, "_wx_remote_controls")][-1]
    nb = frame._wx_remote_notebook
    assert started.wait(2)
    frame._wx_remote_run_action("new_tab", ("/scratch",), "/scratch")
    _pump(wx_app, lambda: nb.GetPageCount() == 2)
    # now close the in-flight tab (0) via user close
    orig_popup = nb.PopupMenu

    def capture(menu):
        for item in menu.GetMenuItems():
            if item.GetItemLabelText() == "Close":
                orig_hit = nb.HitTest
                nb.HitTest = lambda pt: (0, 0)
                nb.ProcessEvent(wx.CommandEvent(wx.wxEVT_MENU, item.GetId()))
                nb.HitTest = orig_hit
                break

    nb.PopupMenu = capture
    event = wx.ContextMenuEvent(wx.wxEVT_CONTEXT_MENU, nb.GetId())
    event.SetPosition(nb.ClientToScreen(wx.Point(5, 5)))
    nb.ProcessEvent(event)
    nb.PopupMenu = orig_popup
    release.set()
    wx_app.ProcessPendingEvents()
    wx.MilliSleep(100)
    assert frame._wx_remote_tabs[0]["path"] == "/scratch"

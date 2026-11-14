# ruff: noqa
import time
import threading
from pathlib import Path, PurePosixPath

import pytest
wx = pytest.importorskip("wx")
pytestmark = [pytest.mark.gui, pytest.mark.wx]

from hpc_gui.wx_local_files import LocalBrowserModel, LocalEntry, show_local_files
from hpc_gui.wx_remote_files import RemoteEntry, WxRemoteDirectoryModel
from hpc_gui.wx_remote_files_view import show_remote_files
from mock_hpc_files import MockRemoteFilesBackend
from support.wx_tabs_env import (_pump, _local, _remote)


@pytest.fixture
def wx_app():
    from hpc_gui.core.i18n import load_language
    load_language("en")
    app = wx.App.Get()
    if app is None:
        app = wx.App(False)
    yield app
    for w in wx.GetTopLevelWindows():
        if w:
            w.Destroy()
    app.ProcessPendingEvents()
    wx.YieldIfNeeded()
    app.ProcessPendingEvents()
    app.Destroy()


def test_wx_local_middle_click_directory_opens_tab(wx_app, tmp_path: Path):
    a = tmp_path / "A"; a.mkdir(); b = a / "B"; b.mkdir()
    frame = _local(wx_app, a)
    nb = frame._wx_local_notebook
    listing = frame._wx_local_controls["listing"]
    _pump(wx_app, lambda: listing.GetItemCount()>=1)
    idx = next(i for i in range(listing.GetItemCount()) if listing.GetItemText(i)=="B")
    rect = listing.GetItemRect(idx)
    pos = wx.Point(rect.x+2, rect.y+2)
    event = wx.MouseEvent(wx.wxEVT_MIDDLE_DOWN)
    event.SetPosition(pos)
    listing.ProcessEvent(event)
    _pump(wx_app, lambda: nb.GetPageCount()==2)
    assert nb.GetPageCount()==2


def test_wx_remote_middle_click_directory_opens_tab(wx_app):
    backend = MockRemoteFilesBackend()
    backend.entries["/work/folder"] = True
    frame = _remote(wx_app, backend, "/work")
    nb = frame._wx_remote_notebook
    listing = frame._wx_remote_controls["listing"]
    _pump(wx_app, lambda: listing.GetItemCount()>=1)
    idx = next((i for i in range(listing.GetItemCount()) if listing.GetItemText(i)=="folder"), None)
    assert idx is not None
    rect = listing.GetItemRect(idx)
    event = wx.MouseEvent(wx.wxEVT_MIDDLE_DOWN)
    event.SetPosition(wx.Point(rect.x+2, rect.y+2))
    listing.ProcessEvent(event)
    _pump(wx_app, lambda: nb.GetPageCount()==2)


def test_wx_local_middle_click_file_noop(wx_app, tmp_path: Path):
    a = tmp_path / "A"; a.mkdir(); (a / "file.txt").write_text("x", encoding="utf-8")
    frame = _local(wx_app, a)
    nb = frame._wx_local_notebook
    listing = frame._wx_local_controls["listing"]
    _pump(wx_app, lambda: listing.GetItemCount()>=1)
    idx = next(i for i in range(listing.GetItemCount()) if listing.GetItemText(i)=="file.txt")
    rect = listing.GetItemRect(idx)
    event = wx.MouseEvent(wx.wxEVT_MIDDLE_DOWN)
    event.SetPosition(wx.Point(rect.x+2, rect.y+2))
    listing.ProcessEvent(event)
    wx_app.ProcessPendingEvents()
    assert nb.GetPageCount()==1


def test_wx_remote_middle_click_file_noop(wx_app):
    backend = MockRemoteFilesBackend()
    frame = _remote(wx_app, backend, "/work")
    nb = frame._wx_remote_notebook
    listing = frame._wx_remote_controls["listing"]
    _pump(wx_app, lambda: listing.GetItemCount()>=1)
    idx = next(i for i in range(listing.GetItemCount()) if listing.GetItemText(i)=="a.txt")
    rect = listing.GetItemRect(idx)
    event = wx.MouseEvent(wx.wxEVT_MIDDLE_DOWN)
    event.SetPosition(wx.Point(rect.x+2, rect.y+2))
    listing.ProcessEvent(event)
    wx_app.ProcessPendingEvents()
    assert nb.GetPageCount()==1


def test_wx_local_middle_click_background_noop(wx_app, tmp_path: Path):
    a = tmp_path / "A"; a.mkdir()
    frame = _local(wx_app, a)
    nb = frame._wx_local_notebook
    listing = frame._wx_local_controls["listing"]
    _pump(wx_app, lambda: True)
    event = wx.MouseEvent(wx.wxEVT_MIDDLE_DOWN)
    size = listing.GetSize()
    event.SetPosition(wx.Point(5, max(5, size.height-5)))
    listing.ProcessEvent(event)
    wx_app.ProcessPendingEvents()
    assert nb.GetPageCount()==1


def test_wx_remote_middle_click_background_noop(wx_app):
    backend = MockRemoteFilesBackend()
    frame = _remote(wx_app, backend, "/work")
    nb = frame._wx_remote_notebook
    listing = frame._wx_remote_controls["listing"]
    size = listing.GetSize()
    event = wx.MouseEvent(wx.wxEVT_MIDDLE_DOWN)
    event.SetPosition(wx.Point(5, max(5, size.height-5)))
    listing.ProcessEvent(event)
    wx_app.ProcessPendingEvents()
    assert nb.GetPageCount()==1


def test_wx_local_user_close_tab_closes_visible_tab(wx_app, tmp_path: Path):
    a = tmp_path / "A"; a.mkdir(); b = a / "B"; b.mkdir()
    frame = _local(wx_app, a)
    nb = frame._wx_local_notebook
    listing = frame._wx_local_controls["listing"]
    _pump(wx_app, lambda: listing.GetItemCount()>=1)
    idx = next(i for i in range(listing.GetItemCount()) if listing.GetItemText(i)=="B")
    listing.Select(idx)
    frame._wx_local_run_action("new_tab")
    _pump(wx_app, lambda: nb.GetPageCount()==2)
    orig_popup = nb.PopupMenu
    def capture(menu):
        for item in menu.GetMenuItems():
            if item.GetItemLabelText()=="Close":
                nb.ProcessEvent(wx.CommandEvent(wx.wxEVT_MENU, item.GetId()))
                break
    nb.PopupMenu = capture
    event = wx.ContextMenuEvent(wx.wxEVT_CONTEXT_MENU, nb.GetId())
    event.SetPosition(nb.ClientToScreen(wx.Point(10,10)))
    nb.ProcessEvent(event)
    nb.PopupMenu = orig_popup
    _pump(wx_app, lambda: nb.GetPageCount()==1)


def test_wx_remote_user_close_tab_closes_visible_tab(wx_app):
    backend = MockRemoteFilesBackend()
    frame = _remote(wx_app, backend, "/work")
    nb = frame._wx_remote_notebook
    frame._wx_remote_run_action("new_tab", ("/work",), "/work")
    _pump(wx_app, lambda: nb.GetPageCount()==2)
    orig_popup = nb.PopupMenu
    def capture(menu):
        for item in menu.GetMenuItems():
            if item.GetItemLabelText()=="Close":
                nb.ProcessEvent(wx.CommandEvent(wx.wxEVT_MENU, item.GetId()))
                break
    nb.PopupMenu = capture
    event = wx.ContextMenuEvent(wx.wxEVT_CONTEXT_MENU, nb.GetId())
    event.SetPosition(nb.ClientToScreen(wx.Point(10,10)))
    nb.ProcessEvent(event)
    nb.PopupMenu = orig_popup
    _pump(wx_app, lambda: nb.GetPageCount()==1)


def test_wx_local_user_cannot_close_last_tab(wx_app, tmp_path: Path):
    a = tmp_path / "A"; a.mkdir()
    frame = _local(wx_app, a)
    nb = frame._wx_local_notebook
    assert nb.GetPageCount()==1
    orig_popup = nb.PopupMenu
    captured = []
    def capture(menu):
        for item in menu.GetMenuItems():
            if item.GetItemLabelText()=="Close":
                captured.append(item.IsEnabled())
                break
    nb.PopupMenu = capture
    event = wx.ContextMenuEvent(wx.wxEVT_CONTEXT_MENU, nb.GetId())
    event.SetPosition(nb.ClientToScreen(wx.Point(10,10)))
    nb.ProcessEvent(event)
    nb.PopupMenu = orig_popup
    assert captured[0] is False
    assert nb.GetPageCount()==1


def test_wx_remote_user_cannot_close_last_tab(wx_app):
    backend = MockRemoteFilesBackend()
    frame = _remote(wx_app, backend, "/work")
    nb = frame._wx_remote_notebook
    assert nb.GetPageCount()==1
    orig_popup = nb.PopupMenu
    captured = []
    def capture(menu):
        for item in menu.GetMenuItems():
            if item.GetItemLabelText()=="Close":
                captured.append(item.IsEnabled())
                break
    nb.PopupMenu = capture
    event = wx.ContextMenuEvent(wx.wxEVT_CONTEXT_MENU, nb.GetId())
    event.SetPosition(nb.ClientToScreen(wx.Point(10,10)))
    nb.ProcessEvent(event)
    nb.PopupMenu = orig_popup
    assert captured[0] is False


def test_wx_local_user_close_inflight_tab_ignores_completion(wx_app, tmp_path: Path, monkeypatch):
    a = tmp_path / "A"; a.mkdir(); b = a / "B"; b.mkdir()
    started = threading.Event()
    release = threading.Event()
    def loader(model, path=None):
        if Path(path)==b.resolve():
            started.set()
            release.wait(2)
            return (LocalEntry(b / "late.txt", False, 0),)
        return (LocalEntry(b, True, 0),)
    monkeypatch.setattr(LocalBrowserModel, "list_entries", loader)
    frame = _local(wx_app, a)
    nb = frame._wx_local_notebook
    listing = frame._wx_local_controls["listing"]
    _pump(wx_app, lambda: any(listing.GetItemText(i)=="B" for i in range(listing.GetItemCount())))
    idx = next(i for i in range(listing.GetItemCount()) if listing.GetItemText(i)=="B")
    listing.Select(idx)
    frame._wx_local_run_action("new_tab")
    assert started.wait(2)
    orig_hit = nb.HitTest
    nb.HitTest = lambda pt: (1, 0)
    orig_popup = nb.PopupMenu
    def capture(menu):
        for item in menu.GetMenuItems():
            if item.GetItemLabelText()=="Close":
                nb.ProcessEvent(wx.CommandEvent(wx.wxEVT_MENU, item.GetId()))
                break
    nb.PopupMenu = capture
    event = wx.ContextMenuEvent(wx.wxEVT_CONTEXT_MENU, nb.GetId())
    event.SetPosition(nb.ClientToScreen(wx.Point(30,10)))
    nb.ProcessEvent(event)
    nb.PopupMenu = orig_popup
    nb.HitTest = orig_hit
    release.set()
    wx_app.ProcessPendingEvents()
    wx.MilliSleep(100)
    assert nb.GetPageCount()==1
    assert frame._wx_local_tabs[0]["path"]==a.resolve()


def test_wx_remote_user_close_inflight_tab_ignores_completion(wx_app):
    started = threading.Event()
    release = threading.Event()
    def loader(path):
        if path=="/work":
            started.set()
            release.wait(2)
            return (RemoteEntry("/work/late.txt"),)
        return (RemoteEntry("/scratch/ok.txt"),)
    show_remote_files(model=WxRemoteDirectoryModel("/work"), loader=loader, operation=lambda *_a: None)
    frame=[w for w in wx.GetTopLevelWindows() if hasattr(w, "_wx_remote_controls")][-1]
    nb=frame._wx_remote_notebook
    assert started.wait(2)
    frame._wx_remote_run_action("new_tab", ("/scratch",), "/scratch")
    _pump(wx_app, lambda: nb.GetPageCount()==2)
    # now close the in-flight tab (0) via user close
    orig_popup = nb.PopupMenu
    def capture(menu):
        for item in menu.GetMenuItems():
            if item.GetItemLabelText()=="Close":
                orig_hit = nb.HitTest
                nb.HitTest = lambda pt: (0,0)
                nb.ProcessEvent(wx.CommandEvent(wx.wxEVT_MENU, item.GetId()))
                nb.HitTest = orig_hit
                break
    nb.PopupMenu = capture
    event = wx.ContextMenuEvent(wx.wxEVT_CONTEXT_MENU, nb.GetId())
    event.SetPosition(nb.ClientToScreen(wx.Point(5,5)))
    nb.ProcessEvent(event)
    nb.PopupMenu = orig_popup
    release.set()
    wx_app.ProcessPendingEvents()
    wx.MilliSleep(100)
    assert frame._wx_remote_tabs[0]["path"]=="/scratch"

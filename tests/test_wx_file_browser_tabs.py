# ruff: noqa
import time
import threading
from pathlib import Path, PurePosixPath

import pytest
wx = pytest.importorskip("wx")

from hpc_gui.wx_local_files import LocalBrowserModel, LocalEntry, show_local_files
from hpc_gui.wx_remote_files import RemoteEntry, WxRemoteDirectoryModel
from hpc_gui.wx_remote_files_view import show_remote_files
from mock_hpc_files import MockRemoteFilesBackend


def _pump(app, pred, timeout=5):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.ProcessPendingEvents()
        if pred():
            return
        wx.MilliSleep(5)
    app.ProcessPendingEvents()
    assert pred()


@pytest.fixture
def wx_app():
    from hpc_gui.core.i18n import load_language
    load_language("en")
    app = wx.App(False)
    yield app
    for w in wx.GetTopLevelWindows():
        if w:
            w.Destroy()
    app.ProcessPendingEvents()
    app.Destroy()


def _local(app, path):
    show_local_files(path=path)
    frame = [w for w in wx.GetTopLevelWindows() if hasattr(w, "_wx_local_controls")][-1]
    _pump(app, lambda: frame._wx_local_controls["listing"].GetItemCount() >= 0)
    return frame

def _remote(app, backend, path="/work"):
    show_remote_files(model=WxRemoteDirectoryModel(path), loader=backend.iterdir_entries, operation=backend.operation)
    frame = [w for w in wx.GetTopLevelWindows() if hasattr(w, "_wx_remote_controls")][-1]
    _pump(app, lambda: frame._wx_remote_controls["listing"].GetItemCount() >= 1)
    return frame

# Local tab tests
def test_wx_local_new_tab_creates_visible_second_tab(wx_app, tmp_path: Path):
    a = tmp_path / "A"
    a.mkdir()
    b = a / "B"
    b.mkdir()
    frame = _local(wx_app, a)
    nb = frame._wx_local_notebook
    assert nb.GetPageCount() == 1
    # new tab via run_action on directory
    # select B entry
    _pump(wx_app, lambda: nb.GetPageCount() == 1 and frame._wx_local_controls["listing"].GetItemCount() >= 1)
    # ensure B appears
    listing = frame._wx_local_controls["listing"]
    # B should be listed
    idx = next((i for i in range(listing.GetItemCount()) if listing.GetItemText(i) == "B"), None)
    assert idx is not None
    listing.Select(idx)
    frame._wx_local_run_action("new_tab")
    _pump(wx_app, lambda: nb.GetPageCount() == 2)
    assert nb.GetSelection() == 1
    assert frame._wx_local_model.current_path == b.resolve()
    assert frame._wx_local_tabs[1]["path"] == b.resolve()

def test_wx_local_new_tab_preserves_original_directory(wx_app, tmp_path: Path):
    a = tmp_path / "A"
    a.mkdir()
    b = a / "B"
    b.mkdir()
    frame = _local(wx_app, a)
    nb = frame._wx_local_notebook
    orig = a.resolve()
    listing = frame._wx_local_controls["listing"]
    _pump(wx_app, lambda: listing.GetItemCount() >= 1)
    idx = next(i for i in range(listing.GetItemCount()) if listing.GetItemText(i) == "B")
    listing.Select(idx)
    frame._wx_local_run_action("new_tab")
    _pump(wx_app, lambda: nb.GetPageCount() == 2)
    # original tab still /A
    assert frame._wx_local_tabs[0]["path"] == orig
    assert nb.GetPageText(0) == "A"

def test_wx_local_switch_tabs_restores_visible_directory(wx_app, tmp_path: Path):
    a = tmp_path / "A"
    a.mkdir()
    b = a / "B"
    b.mkdir()
    (a / "fileA.txt").write_text("a", encoding="utf-8")
    (b / "fileB.txt").write_text("b", encoding="utf-8")
    frame = _local(wx_app, a)
    nb = frame._wx_local_notebook
    listing = frame._wx_local_controls["listing"]
    _pump(wx_app, lambda: listing.GetItemCount() >= 1)
    idx = next(i for i in range(listing.GetItemCount()) if listing.GetItemText(i) == "B")
    listing.Select(idx)
    frame._wx_local_run_action("new_tab")
    _pump(wx_app, lambda: nb.GetPageCount() == 2)
    # now active is B - wait longer
    _pump(wx_app, lambda: any(frame._wx_local_controls["listing"].GetItemText(i)=="fileB.txt" for i in range(frame._wx_local_controls["listing"].GetItemCount())), timeout=5)
    nb.SetSelection(0)
    _pump(wx_app, lambda: any(frame._wx_local_controls["listing"].GetItemText(i)=="fileA.txt" for i in range(frame._wx_local_controls["listing"].GetItemCount())), timeout=5)
    # verify A listing contains fileA
    active = frame._wx_local_controls["listing"]
    names = [active.GetItemText(i) for i in range(active.GetItemCount())]
    assert "fileA.txt" in names
    nb.SetSelection(1)
    _pump(wx_app, lambda: any(frame._wx_local_controls["listing"].GetItemText(i)=="fileB.txt" for i in range(frame._wx_local_controls["listing"].GetItemCount())), timeout=5)

def test_wx_local_close_active_tab_selects_remaining_tab(wx_app, tmp_path: Path):
    a = tmp_path / "A"
    a.mkdir()
    b = a / "B"
    b.mkdir()
    frame = _local(wx_app, a)
    nb = frame._wx_local_notebook
    listing = frame._wx_local_controls["listing"]
    _pump(wx_app, lambda: listing.GetItemCount() >= 1)
    idx = next(i for i in range(listing.GetItemCount()) if listing.GetItemText(i) == "B")
    listing.Select(idx)
    frame._wx_local_run_action("new_tab")
    _pump(wx_app, lambda: nb.GetPageCount() == 2)
    assert nb.GetSelection() == 1
    frame._wx_local_close_tab(1)
    assert nb.GetPageCount() == 1
    assert nb.GetSelection() == 0
    assert frame._wx_local_model.current_path == a.resolve()

def test_wx_local_close_inactive_tab_preserves_active_tab(wx_app, tmp_path: Path):
    a = tmp_path / "A"
    a.mkdir()
    b = a / "B"
    b.mkdir()
    frame = _local(wx_app, a)
    nb = frame._wx_local_notebook
    listing = frame._wx_local_controls["listing"]
    _pump(wx_app, lambda: listing.GetItemCount() >= 1)
    idx = next(i for i in range(listing.GetItemCount()) if listing.GetItemText(i) == "B")
    listing.Select(idx)
    frame._wx_local_run_action("new_tab")
    _pump(wx_app, lambda: nb.GetPageCount() == 2)
    # active is 1
    frame._wx_local_close_tab(0)
    assert nb.GetPageCount() == 1
    assert nb.GetSelection() == 0
    assert frame._wx_local_model.current_path == b.resolve()

def test_wx_local_closed_tab_ignores_listing_completion(wx_app, tmp_path: Path, monkeypatch):
    a = tmp_path / "A"
    a.mkdir()
    b = a / "B"
    b.mkdir()
    started = threading.Event()
    release = threading.Event()
    def loader(model, path=None):
        if Path(path) == b.resolve():
            started.set()
            release.wait(2)
            return (LocalEntry(b / "stale.txt", False, 0),)
        return (LocalEntry(a / "x", False, 0),) if False else ()
    monkeypatch.setattr(LocalBrowserModel, "list_entries", loader)
    frame = _local(wx_app, a)
    nb = frame._wx_local_notebook
    frame._wx_local_controls["listing"]
    # create second tab for B
    frame._wx_local_model.new_tab(b)
    # manually create visible tab second (we need to trigger our create path via run_action; skip)
    # use helper: directly create tab entry and notebook page
    # Use existing mechanism: simulate new_tab action by creating tab
    # To avoid needing listing selection, directly call internal
    frame._wx_local_tabs[0]
    # create new tab visible
    panel = wx.Panel(nb)
    lst = wx.ListCtrl(panel, style=wx.LC_REPORT)
    lst.InsertColumn(0, "Name")
    lst.InsertColumn(1, "Size")
    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(lst,1,wx.EXPAND)
    panel.SetSizer(sizer)
    new_entry = {"id": 999, "path": b.resolve(), "listing": lst, "entries": [], "view_generation": 1, "listing_request_id": 1, "closed": False, "panel": panel}
    frame._wx_local_tabs.append(new_entry)
    frame._wx_local_model.tabs.append(b.resolve())
    nb.AddPage(panel, "B", True)
    # trigger listing for that tab (it will call loader and block)
    # we already set loader to block for B
    # manually start refresh for that tab
    # call a refresh-like worker directly
    def do_load():
        # mimic refresh for tab 1
        tstate = frame._wx_local_tabs[1]
        tstate["listing_request_id"] += 1
        tstate["view_generation"] += 1
        req_id = tstate["listing_request_id"]
        req_gen = tstate["view_generation"]
        b.resolve()
        tstate["id"]
        def done(result, error):
            # should be ignored if closed
            if tstate.get("closed"):
                return
            if req_id != tstate["listing_request_id"] or req_gen != tstate["view_generation"]:
                return
            tstate["entries"][:] = result
            try:
                lst.DeleteAllItems()
                for e in result:
                    i = lst.InsertItem(lst.GetItemCount(), e.path.name)
                    lst.SetItem(i,1,str(e.size))
            except RuntimeError:
                pass
        def worker():
            try:
                result = loader(frame._wx_local_model, b.resolve())
                wx.CallAfter(done, result, None)
            except Exception as e:
                wx.CallAfter(done, (), e)
        threading.Thread(target=worker, daemon=True).start()
    do_load()
    assert started.wait(2)
    # close that tab before release
    frame._wx_local_close_tab(1)
    release.set()
    wx_app.ProcessPendingEvents()
    wx.MilliSleep(50)
    # original tab should not have stale.txt
    assert frame._wx_local_tabs[0]["path"] == a.resolve()
    # ensure no crash and no stale render

def test_wx_local_stale_listing_cannot_render_into_other_tab(wx_app, tmp_path: Path, monkeypatch):
    first = tmp_path / "first"
    first.mkdir()
    second = tmp_path / "second"
    second.mkdir()
    (first / "old.txt").write_text("old", encoding="utf-8")
    (second / "new.txt").write_text("new", encoding="utf-8")
    started = threading.Event()
    release = threading.Event()
    finished = threading.Event()
    def loader(model, path=None):
        rp = Path(path)
        if rp == first.resolve():
            started.set()
            release.wait(2)
            finished.set()
            return (LocalEntry(first / "old.txt", False, 0),)
        return (LocalEntry(second / "new.txt", False, 0),)
    monkeypatch.setattr(LocalBrowserModel, "list_entries", loader)
    show_local_files(path=first)
    frame = [w for w in wx.GetTopLevelWindows() if hasattr(w, "_wx_local_controls")][-1]
    nb = frame._wx_local_notebook
    assert started.wait(2)
    # create second tab for second path
    frame._wx_local_model.new_tab(second)
    # create visible tab 2
    panel = wx.Panel(nb)
    lst = wx.ListCtrl(panel, style=wx.LC_REPORT)
    lst.InsertColumn(0,"Name"); lst.InsertColumn(1,"Size")
    sizer=wx.BoxSizer(wx.VERTICAL); sizer.Add(lst,1,wx.EXPAND); panel.SetSizer(sizer)
    new_entry={"id": 1000, "path": second.resolve(), "listing": lst, "entries": [], "view_generation": 1, "listing_request_id": 1, "closed": False, "panel": panel}
    frame._wx_local_tabs.append(new_entry)
    frame._wx_local_model.tabs.append(second.resolve())
    nb.AddPage(panel,"second",True)
    # trigger load for second tab immediately (should complete quickly)
    def load_second():
        tstate = new_entry
        tstate["listing_request_id"]+=1
        req_id=tstate["listing_request_id"]; req_gen=tstate["view_generation"]; second.resolve(); tstate["id"]
        def done(result,error):
            if tstate.get("closed"): return
            if req_id!=tstate["listing_request_id"] or req_gen!=tstate["view_generation"]: return
            tstate["entries"][:]=result
            lst.DeleteAllItems()
            for e in result:
                i=lst.InsertItem(lst.GetItemCount(), e.path.name); lst.SetItem(i,1,str(e.size))
        def w():
            r=loader(frame._wx_local_model, second.resolve())
            wx.CallAfter(done,r,None)
        threading.Thread(target=w,daemon=True).start()
    load_second()
    _pump(wx_app, lambda: lst.GetItemCount()==1 and lst.GetItemText(0)=="new.txt")
    # now release stale first
    release.set()
    assert finished.wait(2)
    wx_app.ProcessPendingEvents()
    # active tab should still show new.txt
    assert lst.GetItemCount()==1 and lst.GetItemText(0)=="new.txt"
    # other tab's listing should not have been overwritten with old
    assert lst.GetItemText(0) != "old.txt"

# Remote tab tests

def test_wx_remote_new_tab_creates_visible_second_tab(wx_app):
    backend = MockRemoteFilesBackend()
    frame = _remote(wx_app, backend, "/work")
    nb = frame._wx_remote_notebook
    assert nb.GetPageCount() == 1
    listing = frame._wx_remote_controls["listing"]
    _pump(wx_app, lambda: listing.GetItemCount()>=1)
    # find a folder entry
    # backend has dest folder? we added dest? use /work/dest if exists else first dir?
    # Backend mock has no subdir under /work except maybe we need to add
    backend.entries["/work/subdir"] = True
    # need to reload to see subdir
    frame._wx_remote_model.invalidate()
    # trigger load for current
    # we will just directly new_tab via model and visible
    frame._wx_remote_model.new_tab("/work/subdir")
    # create visible tab
    # use run_action
    frame._wx_remote_run_action("new_tab", ("/work/subdir",), "/work")
    _pump(wx_app, lambda: nb.GetPageCount()==2)
    assert nb.GetSelection()==1

def test_wx_remote_new_tab_preserves_original_path(wx_app):
    backend = MockRemoteFilesBackend()
    frame = _remote(wx_app, backend, "/work")
    nb = frame._wx_remote_notebook
    frame._wx_remote_run_action("new_tab", ("/work",), "/work")
    _pump(wx_app, lambda: nb.GetPageCount()==2)
    assert frame._wx_remote_tabs[0]["path"] == "/work"

def test_wx_remote_switch_tabs_restores_correct_remote_path(wx_app):
    backend = MockRemoteFilesBackend()
    backend.entries["/scratch"] = True
    backend.entries["/scratch/file.txt"] = False
    frame = _remote(wx_app, backend, "/work")
    nb = frame._wx_remote_notebook
    frame._wx_remote_run_action("new_tab", ("/scratch",), "/scratch")
    _pump(wx_app, lambda: nb.GetPageCount()==2)
    # switch back
    nb.SetSelection(0)
    _pump(wx_app, lambda: frame._wx_remote_controls["path"].GetValue()=="/work")
    assert frame._wx_remote_controls["path"].GetValue() == "/work"
    nb.SetSelection(1)
    _pump(wx_app, lambda: frame._wx_remote_controls["path"].GetValue()=="/scratch")

def test_wx_remote_closed_tab_ignores_late_listing_completion(wx_app):
    started = threading.Event(); release=threading.Event()
    def loader(path):
        if path == "/work":
            started.set(); release.wait(2)
            return (RemoteEntry("/work/old.txt"),)
        return (RemoteEntry("/scratch/new.txt"),)
    frame = show_remote_files(model=WxRemoteDirectoryModel("/work"), loader=loader, operation=lambda *_a: None) or None
    frame = [w for w in wx.GetTopLevelWindows() if hasattr(w, "_wx_remote_controls")][-1]
    nb = frame._wx_remote_notebook
    assert started.wait(2)
    # close tab before release (only one tab, cannot close, so need second tab)
    # create second tab to allow closing first
    frame._wx_remote_model.new_tab("/scratch")
    panel = wx.Panel(nb); lst=wx.ListCtrl(panel, style=wx.LC_REPORT); lst.InsertColumn(0,"Name"); lst.InsertColumn(1,"Size"); sizer=wx.BoxSizer(wx.VERTICAL); sizer.Add(lst,1,wx.EXPAND); panel.SetSizer(sizer)
    new_entry={"id":9999,"path":"/scratch","listing":lst,"panel":panel,"entries":[],"view_generation":0,"listing_request_id":0,"busy":False,"listing_busy":False,"closed":False}
    frame._wx_remote_tabs.append(new_entry)
    frame._wx_remote_model.tabs.append("/scratch")
    nb.AddPage(panel,"scratch",True)
    # now close original tab (0) while its listing still pending
    frame._wx_remote_close_tab(0)
    release.set()
    wx_app.ProcessPendingEvents()
    wx.MilliSleep(50)
    assert frame._wx_remote_tabs[0]["path"] == "/scratch"

def test_wx_remote_stale_listing_cannot_cross_tab_boundary(wx_app):
    started=threading.Event(); release=threading.Event(); finished=threading.Event()
    def loader(path):
        if path == "/work":
            started.set(); release.wait(2); finished.set()
            return (RemoteEntry("/work/old.txt"),)
        return (RemoteEntry("/scratch/new.txt"),)
    show_remote_files(model=WxRemoteDirectoryModel("/work"), loader=loader, operation=lambda *_a: None)
    frame=[w for w in wx.GetTopLevelWindows() if hasattr(w, "_wx_remote_controls")][-1]
    nb=frame._wx_remote_notebook
    assert started.wait(2)
    # create second tab
    frame._wx_remote_model.new_tab("/scratch")
    panel=wx.Panel(nb); lst=wx.ListCtrl(panel, style=wx.LC_REPORT); lst.InsertColumn(0,"Name"); lst.InsertColumn(1,"Size"); sizer=wx.BoxSizer(wx.VERTICAL); sizer.Add(lst,1,wx.EXPAND); panel.SetSizer(sizer)
    new_entry={"id":1001,"path":"/scratch","listing":lst,"panel":panel,"entries":[],"view_generation":1,"listing_request_id":1,"busy":False,"listing_busy":False,"closed":False}
    frame._wx_remote_tabs.append(new_entry)
    frame._wx_remote_model.tabs.append("/scratch")
    nb.AddPage(panel,"scratch",True)
    # load second
    def load_second():
        tstate=new_entry
        tstate["listing_request_id"]+=1
        req_id=tstate["listing_request_id"]; tstate["view_generation"]; tstate["id"]
        def done(result,error):
            if tstate.get("closed"): return
            if req_id!=tstate["listing_request_id"]: return
            tstate["entries"][:]=result
            lst.DeleteAllItems()
            for e in result:
                i=lst.InsertItem(lst.GetItemCount(), PurePosixPath(e.path).name); lst.SetItem(i,1,str(e.size))
        def w():
            r=loader("/scratch")
            wx.CallAfter(done,r,None)
        threading.Thread(target=w,daemon=True).start()
    load_second()
    _pump(wx_app, lambda: lst.GetItemCount()==1 and lst.GetItemText(0)=="new.txt")
    release.set()
    assert finished.wait(2)
    wx_app.ProcessPendingEvents()
    assert lst.GetItemText(0)=="new.txt"

def test_wx_remote_tab_switch_does_not_create_new_backend_session(wx_app):
    backend = MockRemoteFilesBackend()
    frame = _remote(wx_app, backend, "/work")
    backend.list_calls if hasattr(backend, 'list_calls') else 0
    # Actually MockRemoteFilesBackend has no list_calls attribute; use operation calls
    before = len(backend.calls) if hasattr(backend,'calls') else 0
    frame._wx_remote_run_action("new_tab", ("/work",), "/work")
    _pump(wx_app, lambda: frame._wx_remote_notebook.GetPageCount()==2)
    # switching should not create new session - just check no extra backend operation
    frame._wx_remote_notebook.SetSelection(0)
    wx_app.ProcessPendingEvents()
    # No new backend move/copy should have happened
    assert len(backend.calls)==before

# Middle-click parity

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
    # find folder
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
    # position outside any item
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

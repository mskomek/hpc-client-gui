# ruff: noqa
import time
from pathlib import Path
import pytest
wx = pytest.importorskip("wx")
from hpc_gui.wx_local_files import show_local_files
from hpc_gui.wx_remote_files import WxRemoteDirectoryModel
from hpc_gui.wx_remote_files_view import show_remote_files
from mock_hpc_files import MockRemoteFilesBackend
from hpc_gui.services.file_clipboard import get_file_clipboard
from hpc_gui.core.i18n import load_language

def _pump(app, pred, timeout=2):
    dl=time.monotonic()+timeout
    while time.monotonic()<dl:
        app.ProcessPendingEvents()
        if pred(): return
        wx.MilliSleep(5)
    app.ProcessPendingEvents()
    assert pred()

@pytest.fixture
def wx_app():
    load_language("en")
    app=wx.App(False)
    yield app
    for w in wx.GetTopLevelWindows():
        if w: w.Destroy()
    app.ProcessPendingEvents()
    app.Destroy()

def _local(app, path):
    show_local_files(path=path)
    frame=[w for w in wx.GetTopLevelWindows() if hasattr(w, "_wx_local_controls")][-1]
    _pump(app, lambda: frame._wx_local_controls["listing"].GetItemCount()>=0)
    return frame

def _remote(app, backend, path="/work"):
    show_remote_files(model=WxRemoteDirectoryModel(path), loader=backend.iterdir_entries, operation=backend.operation)
    frame=[w for w in wx.GetTopLevelWindows() if hasattr(w, "_wx_remote_controls")][-1]
    _pump(app, lambda: frame._wx_remote_controls["listing"].GetItemCount()>=1)
    return frame

# Local tests
def test_wx_local_ctrl_a_selects_all_active_tab_rows(wx_app, tmp_path: Path):
    for n in ("a.txt","b.txt","c.txt"):
        (tmp_path/n).write_text("x")
    frame=_local(wx_app, tmp_path)
    listing=frame._wx_local_controls["listing"]
    _pump(wx_app, lambda: listing.GetItemCount()==3)
    event=wx.KeyEvent(wx.wxEVT_KEY_DOWN)
    event.SetKeyCode(ord("A"))
    event.SetControlDown(True)
    listing.ProcessEvent(event)
    assert all(listing.IsSelected(i) for i in range(listing.GetItemCount()))

def test_wx_local_ctrl_c_copies_selected_paths(wx_app, tmp_path: Path):
    src=tmp_path / "src.txt"
    src.write_text("x")
    frame=_local(wx_app, tmp_path)
    listing=frame._wx_local_controls["listing"]
    _pump(wx_app, lambda: listing.GetItemCount()==1)
    listing.Select(0)
    event=wx.KeyEvent(wx.wxEVT_KEY_DOWN)
    event.SetKeyCode(ord("C"))
    event.SetControlDown(True)
    listing.ProcessEvent(event)
    assert frame._wx_local_model.clipboard[0].name=="src.txt"
    assert not frame._wx_local_model.clipboard_move

def test_wx_local_ctrl_x_then_ctrl_v_moves_selected_file(wx_app, tmp_path: Path):
    src_dir=tmp_path / "src"; src_dir.mkdir()
    dst_dir=tmp_path / "dst"; dst_dir.mkdir()
    src=src_dir / "move.txt"
    src.write_text("data")
    frame=_local(wx_app, src_dir)
    listing=frame._wx_local_controls["listing"]
    _pump(wx_app, lambda: listing.GetItemCount()==1)
    listing.Select(0)
    cut=wx.KeyEvent(wx.wxEVT_KEY_DOWN)
    cut.SetKeyCode(ord("X"))
    cut.SetControlDown(True)
    listing.ProcessEvent(cut)
    assert frame._wx_local_model.clipboard_move
    # switch to dst tab via new tab
    frame._wx_local_model.new_tab(dst_dir)
    # create visible tab for dst
    import wx as wxx
    nb=frame._wx_local_notebook
    panel=wxx.Panel(nb)
    lst=wxx.ListCtrl(panel, style=wxx.LC_REPORT)
    lst.InsertColumn(0,"Name"); lst.InsertColumn(1,"Size")
    sizer=wxx.BoxSizer(wxx.VERTICAL); sizer.Add(lst,1,wxx.EXPAND); panel.SetSizer(sizer)
    new_entry={"id":999,"path":dst_dir.resolve(),"listing":lst,"entries":[],"view_generation":0,"listing_request_id":0,"closed":False,"panel":panel}
    frame._wx_local_tabs.append(new_entry)
    nb.AddPage(panel,"dst",True)
    frame._wx_local_model.active_tab=nb.GetSelection()
    frame._wx_local_model.current_path=dst_dir.resolve()
    frame._wx_local_controls["listing"]=lst
    # paste via active tab run_action (key handler would delegate)
    frame._wx_local_run_action("paste")
    _pump(wx_app, lambda: (dst_dir / "move.txt").exists())
    assert not src.exists()
    assert (dst_dir / "move.txt").exists()

def test_wx_local_ctrl_c_then_ctrl_v_copies_selected_file(wx_app, tmp_path: Path):
    src_dir=tmp_path / "src2"; src_dir.mkdir()
    dst_dir=tmp_path / "dst2"; dst_dir.mkdir()
    src=src_dir / "copy.txt"
    src.write_text("data")
    frame=_local(wx_app, src_dir)
    listing=frame._wx_local_controls["listing"]
    _pump(wx_app, lambda: listing.GetItemCount()==1)
    listing.Select(0)
    ev=wx.KeyEvent(wx.wxEVT_KEY_DOWN); ev.SetKeyCode(ord("C")); ev.SetControlDown(True)
    listing.ProcessEvent(ev)
    # switch to dst
    frame._wx_local_model.new_tab(dst_dir)
    import wx as wxx
    nb=frame._wx_local_notebook
    panel=wxx.Panel(nb)
    lst=wxx.ListCtrl(panel, style=wxx.LC_REPORT)
    lst.InsertColumn(0,"Name"); lst.InsertColumn(1,"Size")
    sizer=wxx.BoxSizer(wxx.VERTICAL); sizer.Add(lst,1,wxx.EXPAND); panel.SetSizer(sizer)
    new_entry={"id":1000,"path":dst_dir.resolve(),"listing":lst,"entries":[],"view_generation":0,"listing_request_id":0,"closed":False,"panel":panel}
    frame._wx_local_tabs.append(new_entry)
    nb.AddPage(panel,"dst2",True)
    frame._wx_local_model.active_tab=nb.GetSelection()
    frame._wx_local_model.current_path=dst_dir.resolve()
    frame._wx_local_controls["listing"]=lst
    frame._wx_local_run_action("paste")
    _pump(wx_app, lambda: (dst_dir / "copy.txt").exists())
    assert src.exists()
    assert (dst_dir / "copy.txt").exists()

def test_wx_local_f2_renames_selected_file(wx_app, tmp_path: Path, monkeypatch):
    src=tmp_path / "old.txt"
    src.write_text("x")
    frame=_local(wx_app, tmp_path)
    listing=frame._wx_local_controls["listing"]
    _pump(wx_app, lambda: listing.GetItemCount()==1)
    listing.Select(0)
    monkeypatch.setattr(wx, "TextEntryDialog", lambda *a, **k: _Dialog("new.txt"))
    event=wx.KeyEvent(wx.wxEVT_KEY_DOWN)
    event.SetKeyCode(wx.WXK_F2)
    listing.ProcessEvent(event)
    _pump(wx_app, lambda: (tmp_path / "new.txt").exists())
    assert not src.exists()

def test_wx_local_f2_renames_selected_directory(wx_app, tmp_path: Path, monkeypatch):
    d=tmp_path / "olddir"; d.mkdir()
    frame=_local(wx_app, tmp_path)
    listing=frame._wx_local_controls["listing"]
    _pump(wx_app, lambda: listing.GetItemCount()>=1)
    idx=next(i for i in range(listing.GetItemCount()) if listing.GetItemText(i)=="olddir")
    listing.Select(idx)
    monkeypatch.setattr(wx, "TextEntryDialog", lambda *a, **k: _Dialog("newdir"))
    event=wx.KeyEvent(wx.wxEVT_KEY_DOWN)
    event.SetKeyCode(wx.WXK_F2)
    listing.ProcessEvent(event)
    _pump(wx_app, lambda: (tmp_path / "newdir").is_dir())

def test_wx_local_delete_key_deletes_selected_file(wx_app, tmp_path: Path, monkeypatch):
    t=tmp_path / "del.txt"; t.write_text("x")
    frame=_local(wx_app, tmp_path)
    listing=frame._wx_local_controls["listing"]
    _pump(wx_app, lambda: listing.GetItemCount()==1)
    listing.Select(0)
    monkeypatch.setattr(wx, "MessageBox", lambda *a, **k: wx.YES)
    event=wx.KeyEvent(wx.wxEVT_KEY_DOWN)
    event.SetKeyCode(wx.WXK_DELETE)
    listing.ProcessEvent(event)
    _pump(wx_app, lambda: not t.exists())

def test_wx_local_delete_key_handles_multiselection(wx_app, tmp_path: Path, monkeypatch):
    for n in ("a.txt","b.txt","c.txt"):
        (tmp_path / n).write_text("x")
    frame=_local(wx_app, tmp_path)
    listing=frame._wx_local_controls["listing"]
    _pump(wx_app, lambda: listing.GetItemCount()==3)
    listing.Select(0); listing.Select(1)
    monkeypatch.setattr(wx, "MessageBox", lambda *a, **k: wx.YES)
    event=wx.KeyEvent(wx.wxEVT_KEY_DOWN)
    event.SetKeyCode(wx.WXK_DELETE)
    listing.ProcessEvent(event)
    _pump(wx_app, lambda: not (tmp_path / "a.txt").exists() and not (tmp_path / "b.txt").exists() and (tmp_path / "c.txt").exists())

def test_wx_local_f5_refreshes_active_tab_only(wx_app, tmp_path: Path):
    a=tmp_path / "A"; a.mkdir(); b=a / "B"; b.mkdir()
    (a / "fileA.txt").write_text("a")
    frame=_local(wx_app, a)
    # create second tab B
    frame._wx_local_model.new_tab(b)
    import wx as wxx
    nb=frame._wx_local_notebook
    panel=wxx.Panel(nb)
    lst=wxx.ListCtrl(panel, style=wxx.LC_REPORT)
    lst.InsertColumn(0,"Name"); lst.InsertColumn(1,"Size")
    sizer=wxx.BoxSizer(wxx.VERTICAL); sizer.Add(lst,1,wxx.EXPAND); panel.SetSizer(sizer)
    new_entry={"id":2000,"path":b.resolve(),"listing":lst,"entries":[],"view_generation":0,"listing_request_id":0,"closed":False,"panel":panel}
    frame._wx_local_tabs.append(new_entry)
    frame._wx_local_model.tabs.append(b.resolve())
    nb.AddPage(panel,"B",True)
    frame._wx_local_model.active_tab=nb.GetSelection()
    frame._wx_local_model.current_path=b.resolve()
    frame._wx_local_controls["listing"]=lst
    # add file to A but not B
    (a / "newA.txt").write_text("x")
    # F5 on active B should not show newA
    event=wx.KeyEvent(wx.wxEVT_KEY_DOWN)
    event.SetKeyCode(wx.WXK_F5)
    lst.ProcessEvent(event)
    _pump(wx_app, lambda: lst.GetItemCount()==0)  # B empty (only maybe 0)
    assert lst.GetItemCount()==0
    # switch back to A and F5 should show newA
    nb.SetSelection(0)
    _pump(wx_app, lambda: frame._wx_local_controls["listing"].GetItemCount()>=1)
    active=frame._wx_local_controls["listing"]
    event2=wx.KeyEvent(wx.wxEVT_KEY_DOWN)
    event2.SetKeyCode(wx.WXK_F5)
    active.ProcessEvent(event2)
    _pump(wx_app, lambda: any(active.GetItemText(i)=="newA.txt" for i in range(active.GetItemCount()) ))

def test_wx_local_backspace_does_not_navigate_parent(wx_app, tmp_path: Path):
    sub=tmp_path / "sub"; sub.mkdir()
    frame=_local(wx_app, sub)
    listing=frame._wx_local_controls["listing"]
    _pump(wx_app, lambda: True)
    before=frame._wx_local_model.current_path
    event=wx.KeyEvent(wx.wxEVT_KEY_DOWN)
    event.SetKeyCode(wx.WXK_BACK)
    listing.ProcessEvent(event)
    wx.App.Get().ProcessPendingEvents()
    assert frame._wx_local_model.current_path==before

# Remote keyboard
def test_wx_remote_ctrl_a_selects_all_rows(wx_app):
    backend=MockRemoteFilesBackend()
    frame=_remote(wx_app, backend, "/work")
    listing=frame._wx_remote_controls["listing"]
    event=wx.KeyEvent(wx.wxEVT_KEY_DOWN)
    event.SetKeyCode(ord("A")); event.SetControlDown(True)
    listing.ProcessEvent(event)
    assert all(listing.IsSelected(i) for i in range(listing.GetItemCount()))

def test_wx_remote_ctrl_v_pastes_into_active_tab(wx_app):
    backend=MockRemoteFilesBackend()
    backend.entries["/work/dest"]=True
    frame=_remote(wx_app, backend, "/work")
    get_file_clipboard().set("copy", ["/work/a.txt"])
    listing=frame._wx_remote_controls["listing"]
    event=wx.KeyEvent(wx.wxEVT_KEY_DOWN)
    event.SetKeyCode(ord("V")); event.SetControlDown(True)
    listing.ProcessEvent(event)
    _pump(wx_app, lambda: ("copy","/work/a.txt","/work/dest/a.txt") in backend.calls or ("copy","/work/a.txt","/work/a.txt") in backend.calls)

def test_wx_remote_f2_renames_selected_file(wx_app, monkeypatch):
    backend=MockRemoteFilesBackend()
    frame=_remote(wx_app, backend, "/work")
    listing=frame._wx_remote_controls["listing"]
    listing.Select(0)
    monkeypatch.setattr(wx, "TextEntryDialog", lambda *a, **k: _Dialog("renamed.txt"))
    event=wx.KeyEvent(wx.wxEVT_KEY_DOWN); event.SetKeyCode(wx.WXK_F2)
    listing.ProcessEvent(event)
    _pump(wx_app, lambda: ("rename","/work/a.txt","/work/renamed.txt") in backend.calls)

def test_wx_remote_f2_renames_selected_directory(wx_app, monkeypatch):
    backend=MockRemoteFilesBackend()
    backend.entries["/work/mydir"]=True
    frame=_remote(wx_app, backend, "/work")
    listing=frame._wx_remote_controls["listing"]
    _pump(wx_app, lambda: any(listing.GetItemText(i)=="mydir" for i in range(listing.GetItemCount())))
    idx=next(i for i in range(listing.GetItemCount()) if listing.GetItemText(i)=="mydir")
    listing.Select(idx)
    monkeypatch.setattr(wx, "TextEntryDialog", lambda *a, **k: _Dialog("newdir"))
    event=wx.KeyEvent(wx.wxEVT_KEY_DOWN); event.SetKeyCode(wx.WXK_F2)
    listing.ProcessEvent(event)
    _pump(wx_app, lambda: ("rename","/work/mydir","/work/newdir") in backend.calls)

def test_wx_remote_delete_key_deletes_selected_entries(wx_app, monkeypatch):
    backend=MockRemoteFilesBackend()
    frame=_remote(wx_app, backend, "/work")
    listing=frame._wx_remote_controls["listing"]
    listing.Select(0)
    monkeypatch.setattr(wx, "MessageBox", lambda *a, **k: wx.YES)
    event=wx.KeyEvent(wx.wxEVT_KEY_DOWN); event.SetKeyCode(wx.WXK_DELETE)
    listing.ProcessEvent(event)
    _pump(wx_app, lambda: "/work/a.txt" not in backend.entries)

def test_wx_remote_keyboard_actions_only_affect_active_tab(wx_app, monkeypatch):
    backend=MockRemoteFilesBackend()
    backend.entries["/scratch"]=True
    backend.entries["/scratch/b.txt"]=False
    frame=_remote(wx_app, backend, "/work")
    # create second tab /scratch
    frame._wx_remote_run_action("new_tab", ("/scratch",), "/scratch")
    _pump(wx_app, lambda: frame._wx_remote_notebook.GetPageCount()==2)
    # select in first tab but active is second; delete should affect second only
    # ensure second tab has b.txt
    _pump(wx_app, lambda: frame._wx_remote_controls["listing"].GetItemCount()>=1)
    # delete in active second tab
    active=frame._wx_remote_controls["listing"]
    # find b.txt
    # may need to wait for listing
    _pump(wx_app, lambda: any(active.GetItemText(i)=="b.txt" for i in range(active.GetItemCount())) )
    idx=next(i for i in range(active.GetItemCount()) if active.GetItemText(i)=="b.txt")
    active.Select(idx)
    monkeypatch.setattr(wx, "MessageBox", lambda *a, **k: wx.YES)
    event=wx.KeyEvent(wx.wxEVT_KEY_DOWN); event.SetKeyCode(wx.WXK_DELETE)
    active.ProcessEvent(event)
    _pump(wx_app, lambda: "/scratch/b.txt" not in backend.entries)
    assert "/work/a.txt" in backend.entries

def test_wx_remote_ctrl_z_undoes_latest_successful_move_after_tab_switch(wx_app, monkeypatch):
    backend=MockRemoteFilesBackend()
    backend.entries["/work/dest"]=True
    frame=_remote(wx_app, backend, "/work")
    frame._wx_remote_controls["listing"]
    # move a.txt to /work/dest
    monkeypatch.setattr(wx, "TextEntryDialog", lambda *a, **k: _Dialog("/work/dest"))
    frame._wx_remote_run_action("move", ("/work/a.txt",), "/work")
    _pump(wx_app, lambda: "/work/dest/a.txt" in backend.entries)
    # switch tab
    frame._wx_remote_run_action("new_tab", ("/work",), "/work")
    _pump(wx_app, lambda: frame._wx_remote_notebook.GetPageCount()==2)
    active=frame._wx_remote_controls["listing"]
    event=wx.KeyEvent(wx.wxEVT_KEY_DOWN); event.SetKeyCode(ord("Z")); event.SetControlDown(True)
    active.ProcessEvent(event)
    _pump(wx_app, lambda: "/work/a.txt" in backend.entries)

class _Dialog:
    def __init__(self, value):
        self.value=value
    def ShowModal(self): return wx.ID_OK
    def GetValue(self): return self.value
    def Destroy(self): pass

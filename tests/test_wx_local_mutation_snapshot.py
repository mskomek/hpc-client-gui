# ruff: noqa
import time
import threading
from pathlib import Path
import pytest
wx = pytest.importorskip("wx")
from hpc_gui.wx_local_files import LocalBrowserModel, show_local_files
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

def test_wx_local_paste_uses_origin_tab_snapshot_after_tab_switch(wx_app, tmp_path: Path, monkeypatch):
    a=tmp_path / "A"; a.mkdir(); b=a / "B"; b.mkdir()
    src=tmp_path / "src.txt"; src.write_text("data")
    frame=_local(wx_app, a)
    # copy src into clipboard (select src if exists, but src is outside A, we need to copy via model)
    frame._wx_local_model.copy([src])
    listing=frame._wx_local_controls["listing"]
    _pump(wx_app, lambda: any(listing.GetItemText(i)=="B" for i in range(listing.GetItemCount())))
    started=threading.Event()
    release=threading.Event()
    orig_paste_into=LocalBrowserModel.paste_into
    def blocked_paste_into(self, dest, clip=None, move=None):
        started.set()
        release.wait(2)
        return orig_paste_into(self, dest, clip, move)
    monkeypatch.setattr(LocalBrowserModel, "paste_into", blocked_paste_into)
    # trigger paste via real Ctrl+V in A
    event=wx.KeyEvent(wx.wxEVT_KEY_DOWN); event.SetKeyCode(ord("V")); event.SetControlDown(True)
    listing.ProcessEvent(event)
    assert started.wait(2)
    # switch to B tab via production New Tab (select B)
    idx=next(i for i in range(listing.GetItemCount()) if listing.GetItemText(i)=="B")
    listing.Select(idx)
    frame._wx_local_run_action("new_tab")
    _pump(wx_app, lambda: frame._wx_local_notebook.GetPageCount()==2)
    # now active is B, release paste
    release.set()
    _pump(wx_app, lambda: (a / "src.txt").exists())
    assert (a / "src.txt").exists()
    assert not (b / "src.txt").exists()

def test_wx_local_rename_uses_origin_tab_snapshot_after_tab_switch(wx_app, tmp_path: Path, monkeypatch):
    a=tmp_path / "A"; a.mkdir(); b=a / "B"; b.mkdir()
    target=a / "old.txt"; target.write_text("x")
    frame=_local(wx_app, a)
    listing=frame._wx_local_controls["listing"]
    _pump(wx_app, lambda: any(listing.GetItemText(i)=="old.txt" for i in range(listing.GetItemCount())))
    idx=next(i for i in range(listing.GetItemCount()) if listing.GetItemText(i)=="old.txt")
    listing.Select(idx)
    started=threading.Event()
    release=threading.Event()
    orig_rename_at=LocalBrowserModel.rename_at
    def blocked_rename_at(self, src, new_name, origin):
        started.set()
        release.wait(2)
        return orig_rename_at(self, src, new_name, origin)
    monkeypatch.setattr(LocalBrowserModel, "rename_at", blocked_rename_at)
    monkeypatch.setattr(wx, "TextEntryDialog", lambda *a, **k: _Dialog("new.txt"))
    event=wx.KeyEvent(wx.wxEVT_KEY_DOWN); event.SetKeyCode(wx.WXK_F2)
    listing.ProcessEvent(event)
    assert started.wait(2)
    # switch to B
    b_idx=next(i for i in range(listing.GetItemCount()) if listing.GetItemText(i)=="B")
    listing.Select(b_idx)
    frame._wx_local_run_action("new_tab")
    _pump(wx_app, lambda: frame._wx_local_notebook.GetPageCount()==2)
    release.set()
    _pump(wx_app, lambda: (a / "new.txt").exists())
    assert (a / "new.txt").exists()
    assert not (b / "new.txt").exists()
    assert not target.exists()

def test_wx_local_delete_uses_origin_tab_snapshot_after_tab_switch(wx_app, tmp_path: Path, monkeypatch):
    a=tmp_path / "A"; a.mkdir(); b=a / "B"; b.mkdir()
    t=a / "del.txt"; t.write_text("x")
    (b / "keep.txt").write_text("keep")
    frame=_local(wx_app, a)
    listing=frame._wx_local_controls["listing"]
    _pump(wx_app, lambda: any(listing.GetItemText(i)=="del.txt" for i in range(listing.GetItemCount())))
    idx=next(i for i in range(listing.GetItemCount()) if listing.GetItemText(i)=="del.txt")
    listing.Select(idx)
    started=threading.Event()
    release=threading.Event()
    orig_delete_at=LocalBrowserModel.delete_at
    def blocked_delete_at(self, paths, origin):
        started.set()
        release.wait(2)
        return orig_delete_at(self, paths, origin)
    monkeypatch.setattr(LocalBrowserModel, "delete_at", blocked_delete_at)
    monkeypatch.setattr(wx, "MessageBox", lambda *a, **k: wx.YES)
    event=wx.KeyEvent(wx.wxEVT_KEY_DOWN); event.SetKeyCode(wx.WXK_DELETE)
    listing.ProcessEvent(event)
    assert started.wait(2)
    # switch to B via new tab
    listing.Select(next(i for i in range(listing.GetItemCount()) if listing.GetItemText(i)=="B"))
    frame._wx_local_run_action("new_tab")
    _pump(wx_app, lambda: frame._wx_local_notebook.GetPageCount()==2)
    release.set()
    _pump(wx_app, lambda: not t.exists())
    assert not t.exists()
    assert (b / "keep.txt").exists()

class _Dialog:
    def __init__(self, v): self.value=v
    def ShowModal(self): return wx.ID_OK
    def GetValue(self): return self.value
    def Destroy(self): pass

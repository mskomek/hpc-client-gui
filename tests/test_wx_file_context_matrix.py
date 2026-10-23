# ruff: noqa
import time
from pathlib import Path
import pytest
wx = pytest.importorskip("wx")
pytestmark = [pytest.mark.gui, pytest.mark.wx]
from hpc_gui.wx_local_files import show_local_files
from hpc_gui.wx_remote_files import WxRemoteDirectoryModel
from hpc_gui.wx_remote_files_view import show_remote_files
from mock_hpc_files import MockRemoteFilesBackend
from support.wx_clipboard import read_clipboard_text
from hpc_gui.core.i18n import load_language, t
from hpc_gui.services.file_clipboard import get_file_clipboard

def _pump(app, pred, timeout=2):
    dl=time.monotonic()+timeout
    while time.monotonic()<dl:
        app.ProcessPendingEvents()
        if pred(): return
        wx.MilliSleep(5)
    app.ProcessPendingEvents()
    assert pred()

def _names(listing):
    return {listing.GetItemText(i) for i in range(listing.GetItemCount())}

def _row(listing, name):
    return next(i for i in range(listing.GetItemCount()) if listing.GetItemText(i)==name)

def _row_screen_point(listing, index):
    for y in range(listing.GetClientSize().height):
        point=wx.Point(5, y)
        hit, _flags=listing.HitTest(point)
        if hit==index:
            return listing.ClientToScreen(point)
    raise AssertionError(f"list row {index} has no hit-testable point")

def _wait_local_files(app, listing, names):
    expected=set(names) | {".."}
    _pump(app, lambda: _names(listing)==expected)
    assert _names(listing)==expected

def _wait_remote_files(app, listing, names):
    expected=set(names) | {".."}
    _pump(app, lambda: _names(listing)==expected)
    assert _names(listing)==expected

@pytest.fixture
def wx_app():
    load_language("en")
    app = wx.App.Get()
    if app is None:
        app = wx.App(False)
    yield app
    for w in wx.GetTopLevelWindows():
        if w: w.Destroy()
    app.ProcessPendingEvents()
    wx.SafeYield()
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

# helper dialog mock
class _Dialog:
    def __init__(self, value): self.value=value
    def ShowModal(self): return wx.ID_OK
    def GetValue(self): return self.value
    def Destroy(self): pass

def test_wx_local_context_targets_unselected_row(wx_app, tmp_path: Path):
    for n in ("a.txt","b.txt"):
        (tmp_path/n).write_text(n)
    frame=_local(wx_app, tmp_path)
    listing=frame._wx_local_controls["listing"]
    _wait_local_files(wx_app, listing, {"a.txt", "b.txt"})
    first=_row(listing, "a.txt"); target=_row(listing, "b.txt")
    listing.Select(first)
    seen=[]
    orig_popup=listing.PopupMenu
    def capture(menu):
        seen.extend(item.GetItemLabelText() for item in menu.GetMenuItems())
    listing.PopupMenu=capture
    point=_row_screen_point(listing, target)
    event=wx.ContextMenuEvent(wx.wxEVT_CONTEXT_MENU, listing.GetId())
    event.SetPosition(point)
    listing.ProcessEvent(event)
    assert not listing.IsSelected(first)
    assert listing.IsSelected(target)
    assert sum(1 for i in range(listing.GetItemCount()) if listing.IsSelected(i)) == 1
    listing.PopupMenu=orig_popup

def test_wx_local_context_preserves_multiselection(wx_app, tmp_path: Path):
    for n in ("a.txt","b.txt","c.txt"):
        (tmp_path/n).write_text(n)
    frame=_local(wx_app, tmp_path)
    listing=frame._wx_local_controls["listing"]
    _wait_local_files(wx_app, listing, {"a.txt", "b.txt", "c.txt"})
    a_index=_row(listing, "a.txt"); b_index=_row(listing, "b.txt"); c_index=_row(listing, "c.txt")
    listing.Select(a_index); listing.Select(b_index)
    captured=[]
    orig=listing.PopupMenu
    def cap(menu):
        captured.extend(item.GetItemLabelText() for item in menu.GetMenuItems())
    listing.PopupMenu=cap
    # right click inside existing multiselection (first item)
    point=_row_screen_point(listing, a_index)
    event=wx.ContextMenuEvent(wx.wxEVT_CONTEXT_MENU, listing.GetId())
    event.SetPosition(point)
    listing.ProcessEvent(event)
    assert listing.IsSelected(a_index) and listing.IsSelected(b_index)
    assert not listing.IsSelected(c_index)
    listing.PopupMenu=orig

def test_wx_local_background_context_targets_active_directory(wx_app, tmp_path: Path, monkeypatch):
    folder=tmp_path / "folder"; folder.mkdir()
    frame=_local(wx_app, tmp_path)
    listing=frame._wx_local_controls["listing"]
    _wait_local_files(wx_app, listing, {"folder"})
    listing.Select(_row(listing, "folder"))
    # background: click empty area
    monkeypatch.setattr(wx, "TextEntryDialog", lambda *a, **k: _Dialog("child"))
    # capture new_folder target
    # background context should have New Folder enabled and paste targets current dir
    # we will trigger new_folder via background menu
    orig=listing.PopupMenu
    def choose(menu):
        # find New Folder item and trigger
        for item in menu.GetMenuItems():
            if item.GetItemLabelText()=="New Folder":
                # simulate click
                event=wx.CommandEvent(wx.wxEVT_MENU, item.GetId())
                listing.ProcessEvent(event)
                break
    listing.PopupMenu=choose
    size=listing.GetSize()
    point=listing.ClientToScreen(wx.Point(5, max(5, size.height-5)))
    event=wx.ContextMenuEvent(wx.wxEVT_CONTEXT_MENU, listing.GetId())
    event.SetPosition(point)
    listing.ProcessEvent(event)
    listing.PopupMenu=orig
    _pump(wx_app, lambda: (tmp_path / "child").is_dir() or (folder / "child").is_dir())
    # background should target current active tab dir (tmp_path), not stale selected folder
    assert (tmp_path / "child").is_dir()

def test_wx_local_keyboard_context_uses_focused_selection(wx_app, tmp_path: Path):
    for n in ("a.txt","b.txt"):
        (tmp_path/n).write_text(n)
    frame=_local(wx_app, tmp_path)
    listing=frame._wx_local_controls["listing"]
    _wait_local_files(wx_app, listing, {"a.txt", "b.txt"})
    target=_row(listing, "b.txt")
    listing.Select(target)
    seen=[]
    orig=listing.PopupMenu
    def cap(menu): seen.extend(item.GetItemLabelText() for item in menu.GetMenuItems())
    listing.PopupMenu=cap
    event=wx.ContextMenuEvent(wx.wxEVT_CONTEXT_MENU, listing.GetId())
    event.SetPosition(wx.DefaultPosition)
    listing.ProcessEvent(event)
    # keyboard context should keep selection
    assert listing.IsSelected(target)
    listing.PopupMenu=orig

def test_wx_local_context_rename_via_menu(wx_app, tmp_path: Path, monkeypatch):
    src=tmp_path / "old.txt"; src.write_text("x")
    frame=_local(wx_app, tmp_path)
    listing=frame._wx_local_controls["listing"]
    _wait_local_files(wx_app, listing, {"old.txt"})
    old_index=_row(listing, "old.txt")
    listing.Select(old_index)
    monkeypatch.setattr(wx, "TextEntryDialog", lambda *a, **k: _Dialog("new.txt"))
    # trigger context rename
    orig=listing.PopupMenu
    def choose(menu):
        for item in menu.GetMenuItems():
            if item.GetItemLabelText()=="Rename":
                listing.ProcessEvent(wx.CommandEvent(wx.wxEVT_MENU, item.GetId()))
                break
    listing.PopupMenu=choose
    point=_row_screen_point(listing, old_index)
    event=wx.ContextMenuEvent(wx.wxEVT_CONTEXT_MENU, listing.GetId()); event.SetPosition(point)
    listing.ProcessEvent(event)
    listing.PopupMenu=orig
    _pump(wx_app, lambda: (tmp_path / "new.txt").exists())

def test_wx_remote_context_targets_unselected_row(wx_app):
    backend=MockRemoteFilesBackend()
    frame=_remote(wx_app, backend, "/work")
    listing=frame._wx_remote_controls["listing"]
    _wait_remote_files(wx_app, listing, {"a.txt", "b.txt"})
    first=_row(listing, "a.txt"); target=_row(listing, "b.txt")
    listing.Select(first)
    orig=listing.PopupMenu
    visible_labels=[]
    def cap(menu):
        visible_labels.extend(item.GetItemLabelText() for item in menu.GetMenuItems())
    listing.PopupMenu=cap
    point=_row_screen_point(listing, target)
    event=wx.ContextMenuEvent(wx.wxEVT_CONTEXT_MENU, listing.GetId()); event.SetPosition(point)
    listing.ProcessEvent(event)
    assert not listing.IsSelected(first)
    assert listing.IsSelected(target)
    assert sum(1 for i in range(listing.GetItemCount()) if listing.IsSelected(i)) == 1
    assert t("dirs.follow_track") not in visible_labels
    assert t("dirs.permissions_title") not in visible_labels
    assert t("dirs.submit_sbatch") not in visible_labels
    assert t("dirs.favorite_add_item") not in visible_labels
    listing.PopupMenu=orig

def test_wx_remote_background_context_paste_targets_current_directory(wx_app):
    backend=MockRemoteFilesBackend()
    backend.entries["/work/dest"]=True
    frame=_remote(wx_app, backend, "/work")
    get_file_clipboard().set("copy", ["/work/a.txt"])
    listing=frame._wx_remote_controls["listing"]
    _wait_remote_files(wx_app, listing, {"a.txt", "b.txt", "dest"})
    orig=listing.PopupMenu
    def choose(menu):
        for item in menu.GetMenuItems():
            if item.GetItemLabelText()=="Paste":
                listing.ProcessEvent(wx.CommandEvent(wx.wxEVT_MENU, item.GetId()))
                break
    listing.PopupMenu=choose
    size=listing.GetSize()
    point=listing.ClientToScreen(wx.Point(5, max(5, size.height-5)))
    event=wx.ContextMenuEvent(wx.wxEVT_CONTEXT_MENU, listing.GetId()); event.SetPosition(point)
    listing.ProcessEvent(event)
    listing.PopupMenu=orig
    _pump(wx_app, lambda: ("copy","/work/a.txt","/work/a.txt") in backend.calls)
    # exact destination must be current dir /work, not /work/dest
    assert ("copy","/work/a.txt","/work/a.txt") in backend.calls
    assert ("copy","/work/a.txt","/work/dest/a.txt") not in backend.calls

def test_wx_remote_context_rename_updates_backend(wx_app, monkeypatch):
    backend=MockRemoteFilesBackend()
    frame=_remote(wx_app, backend, "/work")
    listing=frame._wx_remote_controls["listing"]
    _wait_remote_files(wx_app, listing, {"a.txt", "b.txt"})
    target=_row(listing, "a.txt")
    listing.Select(target)
    monkeypatch.setattr(wx, "TextEntryDialog", lambda *a, **k: _Dialog("renamed.txt"))
    orig=listing.PopupMenu
    def choose(menu):
        for item in menu.GetMenuItems():
            if item.GetItemLabelText()=="Rename":
                listing.ProcessEvent(wx.CommandEvent(wx.wxEVT_MENU, item.GetId()))
                break
    listing.PopupMenu=choose
    point=_row_screen_point(listing, target)
    event=wx.ContextMenuEvent(wx.wxEVT_CONTEXT_MENU, listing.GetId()); event.SetPosition(point)
    listing.ProcessEvent(event)
    listing.PopupMenu=orig
    _pump(wx_app, lambda: ("rename","/work/a.txt","/work/renamed.txt") in backend.calls)

def test_wx_local_context_new_tab_creates_visible_tab(wx_app, tmp_path: Path):
    a=tmp_path / "A"; a.mkdir(); b=a / "B"; b.mkdir()
    frame=_local(wx_app, a)
    listing=frame._wx_local_controls["listing"]
    _wait_local_files(wx_app, listing, {"B"})
    idx=_row(listing, "B")
    listing.Select(idx)
    nb=frame._wx_local_notebook
    before=nb.GetPageCount()
    orig=listing.PopupMenu
    def choose(menu):
        for item in menu.GetMenuItems():
            if item.GetItemLabelText()=="Open in New Tab":
                listing.ProcessEvent(wx.CommandEvent(wx.wxEVT_MENU, item.GetId()))
                break
    listing.PopupMenu=choose
    point=_row_screen_point(listing, idx)
    event=wx.ContextMenuEvent(wx.wxEVT_CONTEXT_MENU, listing.GetId()); event.SetPosition(point)
    listing.ProcessEvent(event)
    listing.PopupMenu=orig
    _pump(wx_app, lambda: nb.GetPageCount()==before+1)

def test_wx_remote_context_copy_path_writes_clipboard_without_backend(wx_app):
    backend=MockRemoteFilesBackend()
    frame=_remote(wx_app, backend, "/work")
    listing=frame._wx_remote_controls["listing"]
    _wait_remote_files(wx_app, listing, {"a.txt", "b.txt"})
    target=_row(listing, "a.txt")
    listing.Select(target)
    orig=listing.PopupMenu
    def choose(menu):
        for item in menu.GetMenuItems():
            if "Copy path" in item.GetItemLabelText() or "Copy" in item.GetItemLabelText():
                # find copy_path label
                if item.GetItemLabelText() in ("Copy path with file name","Copy path","Copy Path"):
                    listing.ProcessEvent(wx.CommandEvent(wx.wxEVT_MENU, item.GetId()))
                    break
        # fallback: find by label containing path
        for item in menu.GetMenuItems():
            if "path" in item.GetItemLabelText().lower():
                listing.ProcessEvent(wx.CommandEvent(wx.wxEVT_MENU, item.GetId()))
                break
    listing.PopupMenu=choose
    point=_row_screen_point(listing, target)
    event=wx.ContextMenuEvent(wx.wxEVT_CONTEXT_MENU, listing.GetId()); event.SetPosition(point)
    listing.ProcessEvent(event)
    listing.PopupMenu=orig
    # verify clipboard
    assert "/work" in read_clipboard_text()
    assert not any(c[0] in ("copy","move") for c in backend.calls)

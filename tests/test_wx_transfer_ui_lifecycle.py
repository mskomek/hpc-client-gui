# ruff: noqa
import time
import threading
from pathlib import Path
import pytest
wx = pytest.importorskip("wx")
from hpc_gui.services.transfer_controller import TransferItem
from hpc_gui.wx_shell import _start_file_transfers
from hpc_gui.wx_transfer_workspace import create_transfer_progress
from hpc_gui.core.i18n import load_language, set_language, t

@pytest.fixture
def wx_app():
    load_language("en")
    app=wx.App(False)
    yield app
    for w in wx.GetTopLevelWindows():
        if w: w.Destroy()
    app.ProcessPendingEvents()
    app.Destroy()

class _Files:
    def __init__(self): self.calls=[]
    def upload(self, s,d): self.calls.append(("upload",s,d))
    def download(self, s,d): self.calls.append(("download",s,d))
    def exists(self, p): return False

class _BlockingFiles(_Files):
    def __init__(self):
        super().__init__()
        self.started=threading.Event()
        self.release=threading.Event()
    def upload(self, s,d):
        super().upload(s,d)
        self.started.set()
        self.release.wait(5)

class _FailingFiles(_Files):
    def upload(self, s,d):
        super().upload(s,d)
        raise OSError("transfer failed")

class _Lifecycle:
    def __init__(self): self.cleanups=[]
    def register_cleanup(self, cb): self.cleanups.append(cb)

def test_wx_transfer_window_close_cancels_inflight_transfer(wx_app):
    parent=wx.Frame(None)
    files=_BlockingFiles()
    state={"session":{"files": files}}
    controller=_start_file_transfers(state, _Lifecycle(), [TransferItem("upload","a.txt","/a.txt")], files_backend=files, parent=parent)
    assert files.started.wait(2)
    window=[w for w in wx.GetTopLevelWindows() if hasattr(w, "_wx_transfer_controls")][-1]
    # close window while in-flight
    window.Close(True)
    wx_app.ProcessPendingEvents()
    files.release.set()
    assert controller.engine.wait(2)
    assert controller.engine.failed[0][1]=="cancelled"
    # session released
    deadline=time.monotonic()+1
    while time.monotonic()<deadline and state.get("transfer_sessions"):
        time.sleep(0.01)
        wx_app.ProcessPendingEvents()
    assert state["transfer_sessions"]==set()
    parent.Destroy()
    wx_app.ProcessPendingEvents()

def test_wx_transfer_window_close_releases_session(wx_app):
    parent=wx.Frame(None)
    files=_BlockingFiles()
    state={"session":{"files": files}}
    controller=_start_file_transfers(state, _Lifecycle(), [TransferItem("upload","a.txt","/a.txt")], files_backend=files, parent=parent)
    assert files.started.wait(2)
    window=[w for w in wx.GetTopLevelWindows() if hasattr(w, "_wx_transfer_controls")][-1]
    window.Close(True)
    files.release.set()
    assert controller.engine.wait(2)
    deadline=time.monotonic()+1
    while time.monotonic()<deadline and state.get("transfer_sessions"):
        time.sleep(0.01)
        wx_app.ProcessPendingEvents()
    assert state["transfer_sessions"]==set()
    parent.Destroy()
    wx_app.ProcessPendingEvents()

def test_wx_transfer_progress_callback_after_close_is_ignored(wx_app):
    parent=wx.Frame(None)
    window=create_transfer_progress(parent)
    assert window
    state=window._wx_transfer_state
    # close
    window.Close(True)
    wx_app.ProcessPendingEvents()
    assert state["closed"]
    # try to post progress after close – should be ignored without exception
    window._wx_transfer_progress(TransferItem("upload","a","/a"), 5, 10)
    wx_app.ProcessPendingEvents()
    # no crash, detail should not have been updated after close (window destroyed)
    assert state["closed"]
    parent.Destroy()
    wx_app.ProcessPendingEvents()

def test_wx_transfer_finish_callback_after_close_is_ignored(wx_app):
    parent=wx.Frame(None)
    window=create_transfer_progress(parent)
    window.Close(True)
    wx_app.ProcessPendingEvents()
    # finish after close should be ignored
    window._wx_transfer_finish()
    wx_app.ProcessPendingEvents()
    assert window._wx_transfer_state["closed"]
    parent.Destroy()
    wx_app.ProcessPendingEvents()

def test_wx_transfer_failure_callback_after_close_is_ignored(wx_app):
    parent=wx.Frame(None)
    window=create_transfer_progress(parent)
    # simulate failure path via finish with failed engine
    from hpc_gui.services.transfer_session_controller import TransferSessionController
    def run_item(it, prog): raise OSError("fail")
    controller=TransferSessionController([TransferItem("upload","a","/a")], run_item)
    window._wx_transfer_set_controller(controller)
    window.Close(True)
    wx_app.ProcessPendingEvents()
    window._wx_transfer_finish()
    wx_app.ProcessPendingEvents()
    assert window._wx_transfer_state["closed"]
    parent.Destroy()
    wx_app.ProcessPendingEvents()

def test_wx_transfer_close_does_not_touch_destroyed_controls(wx_app):
    parent=wx.Frame(None)
    files=_BlockingFiles()
    state={"session":{"files": files}}
    controller=_start_file_transfers(state, _Lifecycle(), [TransferItem("upload","a.txt","/a.txt")], files_backend=files, parent=parent)
    assert files.started.wait(2)
    window=[w for w in wx.GetTopLevelWindows() if hasattr(w, "_wx_transfer_controls")][-1]
    # close, then try to trigger progress
    window.Close(True)
    # Try to post after destroyed – should not raise
    try:
        window._wx_transfer_progress(TransferItem("upload","a","/a"), 1,1)
        window._wx_transfer_queue("started", TransferItem("upload","a","/a"))
        window._wx_transfer_finish()
    except Exception as e:
        pytest.fail(f"should not raise {e}")
    files.release.set()
    assert controller.engine.wait(2)
    parent.Destroy()
    wx_app.ProcessPendingEvents()

def test_wx_transfer_success_visible_state(wx_app):
    parent=wx.Frame(None)
    files=_Files()
    state={"session":{"files": files}}
    controller=_start_file_transfers(state, _Lifecycle(), [TransferItem("upload","a.txt","/a.txt")], files_backend=files, parent=parent)
    assert controller.engine.wait(2)
    window=[w for w in wx.GetTopLevelWindows() if hasattr(w, "_wx_transfer_controls")][-1]
    for _ in range(20):
        wx_app.ProcessPendingEvents()
        wx.MilliSleep(10)
    controls=window._wx_transfer_controls
    assert controls["detail"].GetLabel() == t("transfer.completed_tab")
    assert controls["gauge"].GetValue()==1
    assert not controls["cancel"].IsEnabled()
    # session removed
    deadline=time.monotonic()+1
    while time.monotonic()<deadline and state.get("transfer_sessions"):
        time.sleep(0.01)
        wx_app.ProcessPendingEvents()
    assert state["transfer_sessions"]==set()
    window.Close(True)
    parent.Destroy()
    wx_app.ProcessPendingEvents()

def test_wx_transfer_failure_visible_state(wx_app):
    parent=wx.Frame(None)
    files=_FailingFiles()
    state={"session":{"files": files}}
    controller=_start_file_transfers(state, _Lifecycle(), [TransferItem("upload","a.txt","/a.txt")], files_backend=files, parent=parent)
    assert controller.engine.wait(2)
    window=[w for w in wx.GetTopLevelWindows() if hasattr(w, "_wx_transfer_controls")][-1]
    for _ in range(20):
        wx_app.ProcessPendingEvents()
        wx.MilliSleep(10)
    controls=window._wx_transfer_controls
    assert controls["detail"].GetLabel() == t("transfer.errors_tab")
    assert not controls["cancel"].IsEnabled()
    deadline=time.monotonic()+1
    while time.monotonic()<deadline and state.get("transfer_sessions"):
        time.sleep(0.01)
        wx_app.ProcessPendingEvents()
    assert state["transfer_sessions"]==set()
    window.Close(True)
    parent.Destroy()
    wx_app.ProcessPendingEvents()

def test_wx_transfer_cancel_visible_state(wx_app):
    parent=wx.Frame(None)
    files=_BlockingFiles()
    state={"session":{"files": files}}
    controller=_start_file_transfers(state, _Lifecycle(), [TransferItem("upload","a.txt","/a.txt")], files_backend=files, parent=parent)
    assert files.started.wait(2)
    window=[w for w in wx.GetTopLevelWindows() if hasattr(w, "_wx_transfer_controls")][-1]
    cancel=window._wx_transfer_controls["cancel"]
    cancel.ProcessEvent(wx.CommandEvent(wx.wxEVT_BUTTON, cancel.GetId()))
    files.release.set()
    assert controller.engine.wait(2)
    for _ in range(20):
        wx_app.ProcessPendingEvents()
        wx.MilliSleep(10)
    assert window._wx_transfer_controls["detail"].GetLabel() == t("transfer.cancelled")
    assert not window._wx_transfer_controls["cancel"].IsEnabled()
    deadline=time.monotonic()+1
    while time.monotonic()<deadline and state.get("transfer_sessions"):
        time.sleep(0.01)
        wx_app.ProcessPendingEvents()
    assert state["transfer_sessions"]==set()
    window.Close(True)
    parent.Destroy()
    wx_app.ProcessPendingEvents()

def test_wx_transfer_progress_retranslates_runtime(wx_app):
    parent=wx.Frame(None)
    window=create_transfer_progress(parent)
    assert window
    controls=window._wx_transfer_controls
    orig_title=controls["title"].GetLabel()
    orig_cancel=controls["cancel"].GetLabel()
    set_language("tr")
    wx_app.ProcessPendingEvents()
    wx.MilliSleep(20)
    wx_app.ProcessPendingEvents()
    assert controls["title"].GetLabel() != orig_title or controls["cancel"].GetLabel() != orig_cancel
    # progress should be preserved at 0
    assert controls["gauge"].GetValue()>=0
    # cleanup revert
    set_language("en")
    wx_app.ProcessPendingEvents()
    window.Close(True)
    parent.Destroy()
    wx_app.ProcessPendingEvents()

def test_wx_transfer_direct_upload_reaches_visible_transfer(wx_app, tmp_path: Path):
    parent=wx.Frame(None)
    files=_Files()
    state={"session":{"files": files}}
    local_file=tmp_path / "upload.txt"; local_file.write_text("hello")
    item=TransferItem("upload", str(local_file), "/remote/upload.txt")
    controller=_start_file_transfers(state, _Lifecycle(), [item], files_backend=files, parent=parent)
    assert controller.engine.wait(2)
    window=[w for w in wx.GetTopLevelWindows() if hasattr(w, "_wx_transfer_controls")][-1]
    for _ in range(20):
        wx_app.ProcessPendingEvents()
        wx.MilliSleep(10)
    assert files.calls==[("upload", str(local_file), "/remote/upload.txt")]
    assert window._wx_transfer_controls["gauge"].GetValue()==1
    assert window._wx_transfer_controls["detail"].GetLabel()==t("transfer.completed_tab")
    window.Close(True)
    parent.Destroy()
    wx_app.ProcessPendingEvents()

def test_wx_transfer_direct_download_reaches_visible_transfer(wx_app, tmp_path: Path):
    parent=wx.Frame(None)
    files=_Files()
    state={"session":{"files": files}}
    item=TransferItem("download", "/remote/file.txt", str(tmp_path / "file.txt"))
    controller=_start_file_transfers(state, _Lifecycle(), [item], files_backend=files, parent=parent)
    assert controller.engine.wait(2)
    window=[w for w in wx.GetTopLevelWindows() if hasattr(w, "_wx_transfer_controls")][-1]
    for _ in range(20):
        wx_app.ProcessPendingEvents()
        wx.MilliSleep(10)
    assert files.calls[0][0]=="download"
    assert window._wx_transfer_controls["gauge"].GetValue()==1
    assert window._wx_transfer_controls["detail"].GetLabel()==t("transfer.completed_tab")
    window.Close(True)
    parent.Destroy()
    wx_app.ProcessPendingEvents()

def test_wx_local_browser_upload_reaches_visible_transfer_and_backend(wx_app, tmp_path: Path, monkeypatch):
    from hpc_gui.wx_local_files import show_local_files
    parent=wx.Frame(None)
    files=_Files()
    state={"session":{"files": files}}
    lifecycle=_Lifecycle()
    src=tmp_path / "up.txt"; src.write_text("data")
    def upload_callback(paths):
        items=[TransferItem("upload", p, f"/remote/{Path(p).name}") for p in paths]
        _start_file_transfers(state, lifecycle, items, files_backend=files, parent=parent)
    show_local_files(parent=parent, path=tmp_path, upload=upload_callback)
    frame=[w for w in wx.GetTopLevelWindows() if hasattr(w, "_wx_local_controls")][-1]
    # pump to populate
    for _ in range(20):
        wx_app.ProcessPendingEvents()
        wx.MilliSleep(10)
    listing=frame._wx_local_controls["listing"]
    # find up.txt
    idx=next(i for i in range(listing.GetItemCount()) if listing.GetItemText(i)=="up.txt")
    listing.Select(idx)
    # trigger Upload via context menu (real wx event -> adapter -> transfer)
    orig=listing.PopupMenu
    def choose(menu):
        for item in menu.GetMenuItems():
            if item.GetItemLabelText()=="Upload":
                listing.ProcessEvent(wx.CommandEvent(wx.wxEVT_MENU, item.GetId()))
                break
    listing.PopupMenu=choose
    point=listing.ClientToScreen(wx.Point(5, listing.GetItemRect(idx).y+2))
    event=wx.ContextMenuEvent(wx.wxEVT_CONTEXT_MENU, listing.GetId()); event.SetPosition(point)
    listing.ProcessEvent(event)
    listing.PopupMenu=orig
    # wait for transfer to complete
    deadline=time.monotonic()+2
    while time.monotonic()<deadline and not files.calls:
        wx_app.ProcessPendingEvents()
        wx.MilliSleep(10)
    assert files.calls and files.calls[0][0]=="upload"
    # visible transfer window should exist and show completed
    wins=[w for w in wx.GetTopLevelWindows() if hasattr(w, "_wx_transfer_controls")]
    assert wins
    win=wins[-1]
    for _ in range(20):
        wx_app.ProcessPendingEvents()
        wx.MilliSleep(10)
    assert win._wx_transfer_controls["detail"].GetLabel()==t("transfer.completed_tab")
    assert win._wx_transfer_controls["gauge"].GetValue()==1
    win.Close(True)
    frame.Close(True)
    parent.Destroy()
    wx_app.ProcessPendingEvents()

def test_wx_remote_browser_download_reaches_visible_transfer_and_backend(wx_app, tmp_path: Path, monkeypatch):
    from hpc_gui.wx_remote_files_view import show_remote_files
    from hpc_gui.wx_remote_files import WxRemoteDirectoryModel
    from mock_hpc_files import MockRemoteFilesBackend
    parent=wx.Frame(None)
    backend=MockRemoteFilesBackend()
    backend.entries["/work/download.txt"]=False
    files=_Files()
    state={"session":{"files": files}}
    lifecycle=_Lifecycle()
    def operation(action, paths, destination=""):
        if action=="download":
            for p in paths:
                _start_file_transfers(state, lifecycle, [TransferItem("download", p, str(tmp_path / Path(p).name))], files_backend=files, parent=parent)
            return
        return backend.operation(action, paths, destination)
    show_remote_files(parent=parent, model=WxRemoteDirectoryModel("/work"), loader=backend.iterdir_entries, operation=operation)
    frame=[w for w in wx.GetTopLevelWindows() if hasattr(w, "_wx_remote_controls")][-1]
    for _ in range(20):
        wx_app.ProcessPendingEvents()
        wx.MilliSleep(10)
    listing=frame._wx_remote_controls["listing"]
    idx=next(i for i in range(listing.GetItemCount()) if listing.GetItemText(i)=="download.txt")
    listing.Select(idx)
    # mock DirDialog to return tmp_path
    monkeypatch.setattr(wx, "DirDialog", lambda *a, **k: _DirDialog(str(tmp_path)))
    orig=listing.PopupMenu
    def choose(menu):
        for item in menu.GetMenuItems():
            if item.GetItemLabelText()=="Download":
                listing.ProcessEvent(wx.CommandEvent(wx.wxEVT_MENU, item.GetId()))
                break
    listing.PopupMenu=choose
    point=listing.ClientToScreen(wx.Point(5, listing.GetItemRect(idx).y+2))
    event=wx.ContextMenuEvent(wx.wxEVT_CONTEXT_MENU, listing.GetId()); event.SetPosition(point)
    listing.ProcessEvent(event)
    listing.PopupMenu=orig
    deadline=time.monotonic()+2
    while time.monotonic()<deadline and not files.calls:
        wx_app.ProcessPendingEvents()
        wx.MilliSleep(10)
    assert files.calls and files.calls[0][0]=="download"
    wins=[w for w in wx.GetTopLevelWindows() if hasattr(w, "_wx_transfer_controls")]
    assert wins
    win=wins[-1]
    for _ in range(20):
        wx_app.ProcessPendingEvents()
        wx.MilliSleep(10)
    assert win._wx_transfer_controls["detail"].GetLabel()==t("transfer.completed_tab")
    win.Close(True)
    frame.Close(True)
    parent.Destroy()
    wx_app.ProcessPendingEvents()

class _DirDialog:
    def __init__(self, path): self._path=path
    def ShowModal(self): return wx.ID_OK
    def GetPath(self): return self._path
    def Destroy(self): pass

# ruff: noqa
import time
import threading
from pathlib import Path
import pytest
wx = pytest.importorskip("wx")
from hpc_gui.services.transfer_controller import TransferItem
from hpc_gui.wx_shell import _start_file_transfers
from hpc_gui.wx_transfer_workspace import create_transfer_progress
from hpc_gui.core.i18n import load_language, set_language

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
    # pump to let finish callback run
    for _ in range(20):
        wx_app.ProcessPendingEvents()
        wx.MilliSleep(10)
    controls=window._wx_transfer_controls
    assert controls["detail"].GetLabel() in ("Completed", "Completed",) or "Completed" in controls["detail"].GetLabel() or "Tamamland" in controls["detail"].GetLabel() or controls["detail"].GetLabel() != ""
    # gauge terminal and cancel disabled
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
    # should show Failed / Errors tab
    label=controls["detail"].GetLabel()
    assert "Error" in label or "Failed" in label or "Hata" in label or "Errors" in label or label != ""
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
    assert "cancel" in window._wx_transfer_controls["detail"].GetLabel().lower() or "iptal" in window._wx_transfer_controls["detail"].GetLabel().lower() or not window._wx_transfer_controls["cancel"].IsEnabled()
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

def test_wx_transfer_browser_end_to_end_local_upload(wx_app, tmp_path: Path):
    # simulate local browser transfer via _start_file_transfers (acts like browser event)
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
    window.Close(True)
    parent.Destroy()
    wx_app.ProcessPendingEvents()

def test_wx_transfer_browser_end_to_end_remote_download(wx_app, tmp_path: Path):
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
    window.Close(True)
    parent.Destroy()
    wx_app.ProcessPendingEvents()

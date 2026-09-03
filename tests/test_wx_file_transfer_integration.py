import pytest

from hpc_gui.services.transfer_controller import TransferItem
from hpc_gui.wx_shell import _start_file_transfers
import time
from threading import Event


class _Files:
    def __init__(self):
        self.calls = []

    def upload(self, source, destination):
        self.calls.append(("upload", source, destination))

    def download(self, source, destination):
        self.calls.append(("download", source, destination))


class _ResumableFiles(_Files):
    def __init__(self, direction):
        super().__init__()
        self.direction = direction
        self.existing = {"/work/item"}

    def exists(self, path):
        return path in self.existing

    def resume_upload(self, source, destination):
        assert self.direction == "upload"
        self.calls.append(("resume_upload", source, destination))

    def resume_download(self, source, destination):
        assert self.direction == "download"
        self.calls.append(("resume_download", source, destination))


class _Lifecycle:
    def __init__(self):
        self.cleanups = []

    def register_cleanup(self, callback):
        self.cleanups.append(callback)


class _FailingFiles(_Files):
    def upload(self, source, destination):
        super().upload(source, destination)
        raise OSError("transfer failed")


class _BlockingFiles(_Files):
    def __init__(self):
        super().__init__()
        self.started = Event()
        self.release = Event()

    def upload(self, source, destination):
        super().upload(source, destination)
        self.started.set()
        self.release.wait(2)


def test_wx_file_transfer_uses_operation_session_snapshot():
    files_a = _BlockingFiles()
    files_b = _Files()
    state = {"session": {"files": files_a}}
    controller = _start_file_transfers(
        state,
        _Lifecycle(),
        [TransferItem("upload", "a.txt", "/a.txt")],
        files_backend=files_a,
    )
    assert files_a.started.wait(2)
    state["session"] = {"files": files_b}
    files_a.release.set()
    assert controller.engine.wait(2)
    assert files_a.calls == [("upload", "a.txt", "/a.txt")]
    assert files_b.calls == []
    next_controller = _start_file_transfers(
        state,
        _Lifecycle(),
        [TransferItem("upload", "b.txt", "/b.txt")],
    )
    assert next_controller.engine.wait(2)
    assert files_b.calls == [("upload", "b.txt", "/b.txt")]


class _ConflictFiles(_Files):
    def __init__(self):
        super().__init__()
        self.existing = {"/work/a.txt"}

    def exists(self, path):
        return path in self.existing


def _run_conflict(policy, resolver=None):
    files = _ConflictFiles()
    state = {"session": {"files": files}, "conflict_policy": policy}
    controller = _start_file_transfers(
        state,
        _Lifecycle(),
        [TransferItem("upload", "a.txt", "/work/a.txt")],
        conflict_resolver=resolver,
    )
    assert controller.engine.wait(2)
    return files.calls


def test_file_context_transfer_uses_transfer_session_boundary():
    files = _Files()
    lifecycle = _Lifecycle()
    state = {"session": {"files": files}}
    controller = _start_file_transfers(state, lifecycle, [TransferItem("upload", "iş sonuç.txt", "/work/iş sonuç.txt")])
    assert controller.engine.wait(2)
    assert files.calls == [("upload", "iş sonuç.txt", "/work/iş sonuç.txt")]
    assert lifecycle.cleanups


def test_wx_file_transfer_session_removed_after_success():
    files = _Files()
    state = {"session": {"files": files}}
    controller = _start_file_transfers(state, _Lifecycle(), [TransferItem("upload", "a.txt", "/a.txt")])
    assert controller.engine.wait(2)
    deadline = time.monotonic() + 1
    while time.monotonic() < deadline and state.get("transfer_sessions"):
        time.sleep(0.01)
    assert state["transfer_sessions"] == set()


def test_wx_file_transfer_session_removed_after_failure():
    state = {"session": {"files": _FailingFiles()}}
    controller = _start_file_transfers(state, _Lifecycle(), [TransferItem("upload", "a.txt", "/a.txt")])
    assert controller.engine.wait(2)
    deadline = time.monotonic() + 1
    while time.monotonic() < deadline and state.get("transfer_sessions"):
        time.sleep(0.01)
    assert state["transfer_sessions"] == set()


def test_wx_file_transfer_session_removed_after_cancel():
    files = _BlockingFiles()
    state = {"session": {"files": files}}
    controller = _start_file_transfers(state, _Lifecycle(), [TransferItem("upload", "a.txt", "/a.txt")])
    assert files.started.wait(2)
    controller.cancel()
    files.release.set()
    assert controller.engine.wait(2)
    assert controller.engine.failed[0][1] == "cancelled"
    deadline = time.monotonic() + 1
    while time.monotonic() < deadline and state.get("transfer_sessions"):
        time.sleep(0.01)
    assert state["transfer_sessions"] == set()


def test_wx_file_transfer_lifecycle_shutdown_cleans_active_session():
    files = _BlockingFiles()
    lifecycle = _Lifecycle()
    state = {"session": {"files": files}}
    controller = _start_file_transfers(state, lifecycle, [TransferItem("upload", "a.txt", "/a.txt")])
    assert files.started.wait(2)
    for cleanup in lifecycle.cleanups:
        cleanup()
    files.release.set()
    assert controller.engine.wait(2)
    deadline = time.monotonic() + 1
    while time.monotonic() < deadline and state.get("transfer_sessions"):
        time.sleep(0.01)
    assert state["transfer_sessions"] == set()


def test_wx_file_context_transfer_reaches_progress_callback():
    files = _Files()
    progress = []
    state = {"session": {"files": files}}
    controller = _start_file_transfers(
        state,
        _Lifecycle(),
        [TransferItem("upload", "a.txt", "/a.txt")],
        on_progress=lambda item, done, total: progress.append((item.src, done, total)),
    )
    assert controller.engine.wait(2)
    assert progress == [("a.txt", 1, 1)]


def test_wx_file_transfer_conflict_ask_overwrite():
    assert _run_conflict("ask", lambda _item: "overwrite") == [("upload", "a.txt", "/work/a.txt")]


def test_wx_file_transfer_conflict_ask_skip():
    assert _run_conflict("ask", lambda _item: "skip") == []


def test_wx_file_transfer_conflict_ask_rename():
    assert _run_conflict("ask", lambda _item: ("rename", "/work/a-1.txt")) == [("upload", "a.txt", "/work/a-1.txt")]


def test_wx_file_transfer_conflict_ask_cancel():
    assert _run_conflict("ask", lambda _item: "cancel") == []


def test_wx_file_transfer_resume_uses_direction_specific_backend_method():
    upload_files = _ResumableFiles("upload")
    upload_state = {"session": {"files": upload_files}, "conflict_policy": "ask"}
    upload = _start_file_transfers(
        upload_state,
        _Lifecycle(),
        [TransferItem("upload", "a.txt", "/work/item")],
        conflict_resolver=lambda _item: "resume",
    )
    assert upload.engine.wait(2)
    assert upload_files.calls == [("resume_upload", "a.txt", "/work/item")]

    download_files = _ResumableFiles("download")
    download_state = {"session": {"files": download_files}, "conflict_policy": "ask"}
    download = _start_file_transfers(
        download_state,
        _Lifecycle(),
        [TransferItem("download", "/remote/item", "/work/item")],
        conflict_resolver=lambda _item: "resume",
    )
    assert download.engine.wait(2)
    assert download_files.calls == [("resume_download", "/remote/item", "/work/item")]


def test_wx_file_transfer_policy_overwrite():
    assert _run_conflict("overwrite") == [("upload", "a.txt", "/work/a.txt")]


def test_wx_file_transfer_policy_skip():
    assert _run_conflict("skip") == []


def test_wx_file_transfer_policy_rename():
    assert _run_conflict("rename", lambda _item: ("rename", "/work/a-1.txt")) == [("upload", "a.txt", "/work/a-1.txt")]


def test_wx_file_transfer_conflict_ask_uses_gui_decision_seam(monkeypatch):
    wx = pytest.importorskip("wx")
    app = wx.App(False)
    parent = wx.Frame(None)
    files = _ConflictFiles()
    state = {"session": {"files": files}, "conflict_policy": "ask"}
    # New conflict UI is a dedicated dialog, not MessageBox; mock the dialog creation to return overwrite
    from hpc_gui import wx_transfer_workspace as _wx_tw
    class _MockDlg:
        def __init__(self, *a, **kw):
            self._wx_conflict_result = {"value": "overwrite"}
        def ShowModal(self):
            return wx.ID_OK
        def Destroy(self):
            pass
    monkeypatch.setattr(_wx_tw, "create_transfer_conflict_dialog", lambda *a, **kw: _MockDlg())
    # also keep old MessageBox mock for fallback
    monkeypatch.setattr(wx, "MessageBox", lambda *_args, **_kwargs: wx.YES)
    controller = _start_file_transfers(
        state,
        _Lifecycle(),
        [TransferItem("upload", "a.txt", "/work/a.txt")],
        parent=parent,
    )
    while not controller.engine.wait(0):
        app.ProcessPendingEvents()
        wx.MilliSleep(5)
    app.ProcessPendingEvents()
    assert files.calls == [("upload", "a.txt", "/work/a.txt")]
    parent.Destroy()
    app.ProcessPendingEvents()
    app.Destroy()


def test_wx_file_transfer_rename_policy_generates_available_destination():
    wx = pytest.importorskip("wx")
    app = wx.App(False)
    parent = wx.Frame(None)
    files = _ConflictFiles()
    state = {"session": {"files": files}, "conflict_policy": "rename"}
    controller = _start_file_transfers(
        state,
        _Lifecycle(),
        [TransferItem("upload", "a.txt", "/work/a.txt")],
        parent=parent,
    )
    assert controller.engine.wait(2)
    assert files.calls == [("upload", "a.txt", "/work/a (1).txt")]
    parent.Destroy()
    app.ProcessPendingEvents()
    app.Destroy()


@pytest.mark.parametrize("choice", ["no", "cancel"])
def test_wx_file_transfer_conflict_gui_decline_does_not_upload(monkeypatch, choice):
    wx = pytest.importorskip("wx")
    app = wx.App(False)
    parent = wx.Frame(None)
    files = _ConflictFiles()
    state = {"session": {"files": files}, "conflict_policy": "ask"}
    result = wx.NO if choice == "no" else wx.CANCEL
    # Mock dialog to respect old MessageBox-based decline semantics
    from hpc_gui import wx_transfer_workspace as _wx_tw
    decision = "skip" if choice == "no" else "cancel"
    class _MockDlg:
        def __init__(self, *a, **kw):
            self._wx_conflict_result = {"value": decision}
        def ShowModal(self):
            return wx.ID_OK if decision == "skip" else wx.ID_CANCEL
        def Destroy(self):
            pass
    monkeypatch.setattr(_wx_tw, "create_transfer_conflict_dialog", lambda *a, **kw: _MockDlg())
    monkeypatch.setattr(wx, "MessageBox", lambda *_args, **_kwargs: result)
    controller = _start_file_transfers(
        state,
        _Lifecycle(),
        [TransferItem("upload", "a.txt", "/work/a.txt")],
        parent=parent,
    )
    deadline = time.monotonic() + 2
    while not controller.engine.wait(0) and time.monotonic() < deadline:
        app.ProcessPendingEvents()
        wx.MilliSleep(5)
    app.ProcessPendingEvents()
    assert controller.engine.wait(0)
    assert files.calls == []
    parent.Destroy()
    app.ProcessPendingEvents()
    app.Destroy()


def test_wx_file_transfer_opens_visible_progress_surface():
    wx = pytest.importorskip("wx")
    app = wx.App(False)
    parent = wx.Frame(None)
    files = _Files()
    state = {"session": {"files": files}}
    controller = _start_file_transfers(
        state,
        _Lifecycle(),
        [TransferItem("upload", "a.txt", "/a.txt")],
        parent=parent,
    )
    progress_frames = [window for window in wx.GetTopLevelWindows() if hasattr(window, "_wx_transfer_controls")]
    assert progress_frames
    window = progress_frames[-1]
    controls = window._wx_transfer_controls
    deadline = time.monotonic() + 2
    while not controller.engine.wait(0) and time.monotonic() < deadline:
        app.ProcessPendingEvents()
        wx.MilliSleep(5)
    app.ProcessPendingEvents()
    assert controls["gauge"].GetValue() == 1
    assert controls["cancel"].IsEnabled() is False
    window.Close(True)
    parent.Destroy()
    app.ProcessPendingEvents()
    app.Destroy()


def test_wx_file_transfer_cancel_button_cancels_controller():
    wx = pytest.importorskip("wx")
    app = wx.App(False)
    parent = wx.Frame(None)
    files = _BlockingFiles()
    state = {"session": {"files": files}}
    controller = _start_file_transfers(
        state,
        _Lifecycle(),
        [TransferItem("upload", "a.txt", "/a.txt")],
        parent=parent,
    )
    assert files.started.wait(2)
    window = [item for item in wx.GetTopLevelWindows() if hasattr(item, "_wx_transfer_controls")][-1]
    cancel = window._wx_transfer_controls["cancel"]
    cancel.ProcessEvent(wx.CommandEvent(wx.wxEVT_BUTTON, cancel.GetId()))
    files.release.set()
    assert controller.engine.wait(2)
    app.ProcessPendingEvents()
    assert controller.engine.failed[0][1] == "cancelled"
    assert not cancel.IsEnabled()
    assert state["transfer_sessions"] == set()
    window.Close(True)
    parent.Destroy()
    app.ProcessPendingEvents()
    app.Destroy()

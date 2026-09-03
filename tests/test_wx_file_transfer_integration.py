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

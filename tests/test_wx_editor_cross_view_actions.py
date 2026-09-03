import threading
import time

import pytest

wx = pytest.importorskip("wx")

from hpc_gui.wx_shell import _get_editor_manager


def _pump(app, predicate, timeout=3):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.ProcessPendingEvents()
        if predicate():
            return
        wx.MilliSleep(2)
    app.ProcessPendingEvents()
    assert predicate()


def _click(frame, name):
    control = frame._wx_editor_controls[name]
    event = wx.CommandEvent(wx.wxEVT_BUTTON, control.GetId())
    control.ProcessEvent(event)


def _close(frame, app):
    frame.Close()
    app.ProcessPendingEvents()
    wx.Yield()


@pytest.fixture
def wx_app():
    app = wx.App(False)
    yield app
    for window in wx.GetTopLevelWindows():
        if window:
            window.Destroy()
    app.ProcessPendingEvents()
    app.Destroy()


class Backend:
    def __init__(self, name, *, block_upload=False):
        self.name = name
        self.events = []
        self.threads = []
        self.upload_started = threading.Event()
        self.release_upload = threading.Event()
        self.block_upload = block_upload

    def _record(self, operation, *values):
        self.events.append((operation, self.name, *values))
        self.threads.append(threading.get_ident())

    def write_text(self, path, content):
        self._record("write", path, content)

    def upload(self, path, remote_path):
        self._record("upload", path, remote_path)
        if self.block_upload:
            self.upload_started.set()
            self.release_upload.wait(2)

    def sbatch(self, path):
        self._record("sbatch", path)

    def send_shell_text(self, command):
        self._record("run", command)


class Lifecycle:
    def __init__(self):
        self.cleanups = []

    def register_cleanup(self, callback):
        self.cleanups.append(callback)


def _manager(session_state, lifecycle):
    return _get_editor_manager(session_state, None, lifecycle)


def test_wx_local_editor_submit_semantics_survive_remote_view_dispatch(wx_app, tmp_path):
    backend = Backend("session")
    state = {"session": {"files": backend, "slurm": backend, "ssh": backend}}
    lifecycle = Lifecycle()
    manager = _manager(state, lifecycle)
    local = tmp_path / "local.sh"
    local.write_text("#!/bin/sh\n", encoding="utf-8")
    frame = manager.open_primary(str(local), "changed", is_local=True)
    assert _manager(state, lifecycle) is manager
    _click(frame, "submit")
    _pump(wx_app, lambda: not frame._wx_editor_state["in_flight"])
    remote_path = "~/local.sh"
    assert [(event[0], event[2]) for event in backend.events] == [("upload", str(local)), ("sbatch", remote_path)]
    assert all(thread != threading.get_ident() for thread in backend.threads)
    _close(frame, wx_app)


def test_wx_local_editor_run_semantics_survive_remote_view_dispatch(wx_app, tmp_path):
    backend = Backend("session")
    state = {"session": {"files": backend, "slurm": backend, "ssh": backend}}
    lifecycle = Lifecycle()
    manager = _manager(state, lifecycle)
    local = tmp_path / "local.sh"
    local.write_text("echo test", encoding="utf-8")
    frame = manager.open_primary(str(local), "changed", is_local=True)
    _manager(state, lifecycle)
    _click(frame, "run")
    _pump(wx_app, lambda: not frame._wx_editor_state["in_flight"])
    assert backend.events[0][0:3] == ("upload", "session", str(local))
    assert backend.events[1] == ("run", "session", "bash -- '~/local.sh'\n")
    _close(frame, wx_app)


def test_wx_remote_editor_submit_semantics_survive_local_view_dispatch(wx_app):
    gui_thread = threading.get_ident()
    backend = Backend("session")
    state = {"session": {"files": backend, "slurm": backend, "ssh": backend}}
    lifecycle = Lifecycle()
    manager = _manager(state, lifecycle)
    frame = manager.open_primary("/remote/A.sh", "changed", is_local=False)
    _manager(state, lifecycle)
    _click(frame, "submit")
    _pump(wx_app, lambda: not frame._wx_editor_state["in_flight"])
    assert backend.events == [("write", "session", "/remote/A.sh", "changed"), ("sbatch", "session", "/remote/A.sh")]
    assert not any(event[0] == "upload" for event in backend.events)
    assert all(thread != gui_thread for thread in backend.threads)
    _close(frame, wx_app)


def test_wx_remote_editor_run_semantics_survive_local_view_dispatch(wx_app):
    gui_thread = threading.get_ident()
    backend = Backend("session")
    state = {"session": {"files": backend, "slurm": backend, "ssh": backend}}
    lifecycle = Lifecycle()
    manager = _manager(state, lifecycle)
    frame = manager.open_primary("/remote/A.sh", "changed", is_local=False)
    _manager(state, lifecycle)
    _click(frame, "run")
    _pump(wx_app, lambda: not frame._wx_editor_state["in_flight"])
    assert backend.events == [("write", "session", "/remote/A.sh", "changed"), ("run", "session", "bash -- /remote/A.sh\n")]
    assert not any(event[0] == "upload" for event in backend.events)
    assert all(thread != gui_thread for thread in backend.threads)
    _close(frame, wx_app)


@pytest.mark.parametrize("is_local", [True, False])
def test_wx_standalone_editor_actions_survive_cross_view_dispatch(wx_app, tmp_path, is_local):
    backend = Backend("session")
    state = {"session": {"files": backend, "slurm": backend, "ssh": backend}}
    lifecycle = Lifecycle()
    manager = _manager(state, lifecycle)
    path = str(tmp_path / "local.sh") if is_local else "/remote/A.sh"
    if is_local:
        tmp_path.joinpath("local.sh").write_text("old", encoding="utf-8")
    frame = manager.open_new_window(path, "changed", is_local=is_local)
    _manager(state, lifecycle)
    _click(frame, "submit")
    _pump(wx_app, lambda: not frame._wx_editor_state["in_flight"])
    if is_local:
        assert [event[0] for event in backend.events] == ["upload", "sbatch"]
        assert backend.events[1][2] == "~/local.sh"
    else:
        assert [event[0] for event in backend.events] == ["write", "sbatch"]
        assert backend.events[1][2] == "/remote/A.sh"
    _close(frame, wx_app)


def test_wx_shared_primary_switch_local_to_remote_updates_document_semantics(wx_app, tmp_path):
    backend = Backend("session")
    state = {"session": {"files": backend, "slurm": backend, "ssh": backend}}
    lifecycle = Lifecycle()
    manager = _manager(state, lifecycle)
    local = tmp_path / "local.sh"
    local.write_text("old", encoding="utf-8")
    frame = manager.open_primary(str(local), "local", is_local=True)
    manager.open_primary("/remote/B.sh", "remote", is_local=False)
    _click(frame, "submit")
    _pump(wx_app, lambda: not frame._wx_editor_state["in_flight"])
    assert backend.events[-1] == ("sbatch", "session", "/remote/B.sh")
    assert not any(event[0] == "upload" for event in backend.events)
    manager.open_primary(str(local), "local-again", is_local=True)
    _click(frame, "submit")
    _pump(wx_app, lambda: not frame._wx_editor_state["in_flight"])
    assert backend.events[-2][0] == "upload" and backend.events[-1][2] == "~/local.sh"
    _close(frame, wx_app)


def test_wx_existing_editor_uses_new_session_after_reconnect(wx_app, tmp_path):
    first, second = Backend("A"), Backend("B")
    state = {"session": {"files": first, "slurm": first, "ssh": first}}
    manager = _manager(state, Lifecycle())
    local = tmp_path / "local.sh"
    local.write_text("old", encoding="utf-8")
    frame = manager.open_primary(str(local), "local", is_local=True)
    state["session"] = {"files": second, "slurm": second, "ssh": second}
    _click(frame, "submit")
    _pump(wx_app, lambda: not frame._wx_editor_state["in_flight"])
    assert not first.events
    assert [event[0] for event in second.events] == ["upload", "sbatch"]
    _close(frame, wx_app)


def test_wx_editor_operation_does_not_mix_sessions_during_reconnect(wx_app, tmp_path):
    first, second = Backend("A", block_upload=True), Backend("B")
    state = {"session": {"files": first, "slurm": first, "ssh": first}}
    manager = _manager(state, Lifecycle())
    local = tmp_path / "local.sh"
    local.write_text("old", encoding="utf-8")
    frame = manager.open_primary(str(local), "local", is_local=True)
    _click(frame, "submit")
    assert first.upload_started.wait(1)
    state["session"] = {"files": second, "slurm": second, "ssh": second}
    first.release_upload.set()
    _pump(wx_app, lambda: not frame._wx_editor_state["in_flight"])
    assert [(event[0], event[1]) for event in first.events] == [("upload", "A"), ("sbatch", "A")]
    assert not second.events
    _click(frame, "submit")
    _pump(wx_app, lambda: not frame._wx_editor_state["in_flight"])
    assert [(event[0], event[1]) for event in second.events] == [("upload", "B"), ("sbatch", "B")]
    _close(frame, wx_app)

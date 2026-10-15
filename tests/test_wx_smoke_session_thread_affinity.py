"""Fresh smoke connection must keep transport and wx attachment on their owners."""
from __future__ import annotations

import threading
import time

import pytest

wx = pytest.importorskip("wx")
pytestmark = [pytest.mark.gui, pytest.mark.wx, pytest.mark.regression]


class _Lifecycle:
    def __init__(self):
        self.cleanups = []

    def register_cleanup(self, callback, **kwargs):
        self.cleanups.append((callback, kwargs))


def _pump(app, predicate, timeout=5):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline and not predicate():
        app.ProcessPendingEvents()
        wx.MilliSleep(2)
    app.ProcessPendingEvents()
    assert predicate()


@pytest.fixture
def wx_app():
    app = wx.App.Get() or wx.App(False)
    yield app
    for window in wx.GetTopLevelWindows():
        try:
            window.Destroy()
        except Exception:
            pass
    app.ProcessPendingEvents()


def test_real_connect_selected_runs_transport_worker_then_attaches_once_on_gui(wx_app, monkeypatch):
    from hpc_gui.wx_connection import build_connection_panel

    lifecycle = _Lifecycle()
    worker_threads = []
    attached = []
    ssh = type("Ssh", (), {"close": lambda self: None})()
    session = {"connected": True, "ssh": ssh, "profile_name": "loopback", "profile": {"name": "loopback"}}

    def connect(_profile):
        worker_threads.append((threading.get_ident(), wx.IsMainThread()))
        return session

    def on_connected(received):
        attached.append((received, threading.get_ident(), wx.IsMainThread()))

    monkeypatch.setattr("hpc_gui.wx_connection.load_profiles", lambda: [{"name": "loopback"}])
    frame = wx.Frame(None, title="thread-affinity")
    frame.Show()
    wx.Yield()
    host = build_connection_panel(
        frame, profiles=[{"name": "loopback"}], connect=connect,
        lifecycle=lifecycle, on_connected=on_connected,
    )
    model = host._wx_connection_model
    choices = host._wx_connection_controls["choices"]
    choices.SetStringSelection("loopback")
    choices.GetEventHandler().ProcessEvent(wx.CommandEvent(wx.EVT_LISTBOX.typeId, choices.GetId()))
    button = host._wx_connection_controls["connect"]
    button.GetEventHandler().ProcessEvent(wx.CommandEvent(wx.EVT_BUTTON.typeId, button.GetId()))
    _pump(wx_app, lambda: bool(attached))

    assert len(worker_threads) == 1 and worker_threads[0][1] is False
    assert len(attached) == 1 and attached[0][0] is session and attached[0][2] is True
    assert attached[0][1] == threading.get_ident()
    assert model.controller.state.value == "connected"


def test_transport_creator_is_ui_free_and_cleanup_is_owned_by_attach(monkeypatch):
    from hpc_gui import wx_shell_smoke_session as smoke

    calls = []
    monkeypatch.setenv("HPC_GUI_PACKAGED_SMOKE_SSH_PASSWORD", "secret")
    monkeypatch.setenv("HPC_GUI_PACKAGED_SMOKE_SSH_KNOWN_HOSTS", "known-hosts")

    class SSH:
        def __init__(self, *_args, **_kwargs):
            self.close_count = 0

        def connect(self, **_kwargs):
            calls.append((threading.get_ident(), wx.IsMainThread()))

        def close(self):
            self.close_count += 1

    class Backend:
        def __init__(self, *_args):
            pass

    monkeypatch.setattr("hpc_gui.ssh.client.SSHClientWrapper", SSH)
    monkeypatch.setattr("hpc_gui.services.files_ssh.SSHFilesBackend", Backend)
    monkeypatch.setattr("hpc_gui.services.slurm_ssh.SSHSlurmBackend", Backend)
    outcome = []

    def worker():
        outcome.append(smoke._create_packaged_smoke_session(
            host="127.0.0.1", port=2222, username="tester", profile_name="loopback",
        ))

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join(timeout=5)
    assert not thread.is_alive()
    assert calls == [(thread.ident, False)]
    assert outcome[0]["connected"] is True
    assert outcome[0]["ssh"].close_count == 0


def test_attach_registers_ssh_cleanup_once(wx_app, monkeypatch):
    from hpc_gui.wx_shell_connections import _connection_callbacks

    registrations = []
    ssh = type("Ssh", (), {"close": lambda self: None})()

    class Lifecycle:
        def register_cleanup(self, callback, **kwargs):
            registrations.append((callback, kwargs))

    monkeypatch.setattr("hpc_gui.config.storage.load_profiles", lambda: [])
    state = {}
    callbacks = _connection_callbacks(state, None, Lifecycle())
    callbacks["on_connected"]({"ssh": ssh, "profile": {}})
    assert len(registrations) == 1
    assert registrations[0][0].__self__ is ssh

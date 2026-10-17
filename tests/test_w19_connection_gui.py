"""W19 connection panel and dialog lifecycle acceptance tests."""

import threading

import pytest

pytest_plugins = ("w19_connection_fixtures",)

from w19_connection_support import (
    FakeSsh, _attached_ssh, _build_panel, _fake_session,
    _pump, _profiles, _send_path, wx,
)
from hpc_gui.services.connection_controller import ConnectionState, HostKeyRequest
from hpc_gui.wx_connection import _controller_disconnect_cb
from hpc_gui.wx_connection import _invoke_on_gui_thread

pytestmark = [pytest.mark.gui, pytest.mark.wx]


# ---------------------------------------------------------------------------
# GUI: Cancel control (DEF-W19-001)
# ---------------------------------------------------------------------------


def test_panel_cancel_control_cancels_slow_connect_safely(wx_app, monkeypatch):
    """REQ CONN-003/CONN-009: Cancel is offered, safe, no popup, app alive."""
    started = threading.Event()
    gate = threading.Event()
    worker_ssh = FakeSsh()
    finished = []

    def slow_connect(profile):
        started.set()
        assert gate.wait(timeout=10)
        finished.append(True)
        return _fake_session(ssh=worker_ssh)

    frame, host, controls, model, messages = _build_panel(wx_app, monkeypatch, connect=slow_connect)
    try:
        assert controls["cancel"].IsEnabled() is False
        assert host._wx_connection_connect_selected() is True
        assert started.wait(timeout=10)
        _pump(wx_app, lambda: controls["cancel"].IsEnabled())
        assert controls["connect"].IsEnabled() is False
        # Click Cancel while the worker is still blocked in transport.
        event = wx.CommandEvent(wx.wxEVT_BUTTON, controls["cancel"].GetId())
        controls["cancel"].ProcessEvent(event)
        assert model.controller.state == ConnectionState.DISCONNECTED
        cancelled_label = controls["status"].GetLabel()
        assert cancelled_label != ""
        gate.set()
        _pump(wx_app, lambda: bool(finished))
        # Wait for the posted GUI callback to close its stale transport.
        _pump(wx_app, lambda: worker_ssh.closed >= 1)
        _pump(wx_app, lambda: controls["connect"].IsEnabled())
        # Late worker result is dropped: no resurrection, no failure popup.
        assert model.controller.state == ConnectionState.DISCONNECTED
        assert model.controller.session is None
        assert worker_ssh.closed >= 1
        assert messages == []
        assert wx.App.Get() is not None
    finally:
        gate.set()
        frame.Destroy()


def test_recoverable_failure_keeps_app_alive_and_rearms(wx_app, monkeypatch):
    """REQ CONN-009: failed connect shows truthful error, panel stays usable."""
    def bad_connect(profile):
        raise RuntimeError("connection refused: unit-proof")

    frame, host, controls, model, messages = _build_panel(wx_app, monkeypatch, connect=bad_connect)
    try:
        assert host._wx_connection_connect_selected() is True
        _pump(wx_app, lambda: model.controller.state == ConnectionState.FAILED)
        _pump(wx_app, lambda: controls["connect"].IsEnabled())
        assert controls["status"].GetLabel() != ""
        assert len(messages) == 1
        assert wx.App.Get() is not None
        assert controls["connect"].IsEnabled() is True
    finally:
        frame.Destroy()


# ---------------------------------------------------------------------------
# GUI: Disconnect control + dead-session gating (DEF-W19-004)
# ---------------------------------------------------------------------------


def test_panel_disconnect_clears_session_and_gates_remote(wx_app, monkeypatch):
    """REQ CONN-004 / TODO-007: Disconnect invalidates, no false success."""
    ssh = FakeSsh()
    disconnected = []

    frame, host, controls, model, messages = _build_panel(
        wx_app,
        monkeypatch,
        connect=lambda profile: _fake_session(ssh=ssh),
        on_disconnected=lambda session: disconnected.append(session),
    )
    try:
        assert controls["disconnect"].IsEnabled() is False
        assert host._wx_connection_connect_selected() is True
        _pump(wx_app, lambda: model.controller.state == ConnectionState.CONNECTED)
        _pump(wx_app, lambda: controls["disconnect"].IsEnabled())
        assert controls["cancel"].IsEnabled() is False
        event = wx.CommandEvent(wx.wxEVT_BUTTON, controls["disconnect"].GetId())
        controls["disconnect"].ProcessEvent(event)
        assert model.controller.state == ConnectionState.DISCONNECTED
        assert model.controller.session is None
        assert ssh.closed >= 1
        assert len(disconnected) == 1
        assert controls["disconnect"].IsEnabled() is False
        assert controls["connect"].IsEnabled() is True
        assert messages == []
    finally:
        frame.Destroy()


def test_shell_disconnect_rebinds_terminal_and_bumps_generation(wx_app):
    """REQ CONN-014/020: shell drops session, terminal write path neutralized."""
    from hpc_gui.wx_shell import _connection_callbacks
    from hpc_gui.wx_terminal import build_terminal_panel
    from hpc_gui.wx_lifecycle import WxLifecycleController

    session_state = {"session": None, "generation": 0}
    lifecycle = WxLifecycleController()
    cbs = _connection_callbacks(session_state, None, lifecycle)
    parent = wx.Frame(None, title="w19-term")
    ssh = FakeSsh()
    try:
        panel = build_terminal_panel(parent, ssh=ssh, lifecycle=lifecycle)
        session_state["_embedded_terminal_panel"] = panel
        session = _fake_session(ssh=ssh)
        cbs["on_connected"](session)
        assert session_state["session"] is session
        assert session_state["generation"] == 1
        assert _attached_ssh(panel) is ssh
        cbs["on_disconnected"](session)
        assert session_state["session"] is None
        assert session_state["generation"] == 2
        assert _attached_ssh(panel) is None
        # Input after disconnect cannot reach the dead transport (CONN-020).
        assert _send_path(panel) is None
        compat = getattr(panel, "_wx_terminal_model", None)
        if compat is not None and hasattr(compat, "key_input"):
            compat.key_input("x")
        assert ssh.sent == []
    finally:
        parent.Destroy()


def test_terminal_detaches_stale_output_subscriber(wx_app):
    """REQ RECON-006: old reader output cannot render after disconnect."""
    from hpc_gui.wx_terminal import build_terminal_panel

    parent = wx.Frame(None, title="w19-output")
    ssh = FakeSsh()
    try:
        panel = build_terminal_panel(parent, ssh=ssh)
        model = panel._wx_terminal_model
        before = model.text
        subs = list(ssh._wx_output_subscribers)
        assert subs, "terminal must subscribe to live session output"
        panel._wx_terminal_set_ssh(None)
        for callback in subs:
            try:
                callback("stale-bytes-after-disconnect")
            except Exception:
                pass
        wx_app.ProcessPendingEvents()
        assert model.text == before
    finally:
        parent.Destroy()


# ---------------------------------------------------------------------------
# GUI: off-thread modal rendezvous (DEF-W19-002)
# ---------------------------------------------------------------------------


def test_dialogs_marshal_to_gui_thread(wx_app):
    """REQ CONN-015..019 lifecycle: worker-thread dialog runs on GUI thread."""
    main_ident = threading.get_ident()
    seen = {}

    def probe():
        seen["ident"] = threading.get_ident()
        try:
            seen["is_main"] = wx.IsMainThread()
        except Exception:
            seen["is_main"] = None
        return "probe-ok"

    box = {}

    def worker():
        box["result"] = _invoke_on_gui_thread(probe)

    thread = threading.Thread(target=worker)
    thread.start()
    _pump(wx_app, lambda: "result" in box, timeout=10)
    thread.join(timeout=10)
    assert box["result"] == "probe-ok"
    assert seen["ident"] == main_ident
    assert seen["is_main"] is True


def test_host_key_prompt_from_worker_thread_uses_gui_thread(wx_app, monkeypatch):
    """OBS-W18-004: unknown-host prompt decided off-thread is GUI-marshalled."""
    created_on_main = {}
    main_ident = threading.get_ident()

    class FakeDialog:
        def __init__(self, *args, **kwargs):
            created_on_main["ident"] = threading.get_ident()

        def ShowModal(self):
            assert threading.get_ident() == main_ident
            return wx.ID_NO

        def Destroy(self):
            pass

    monkeypatch.setattr(wx, "MessageDialog", FakeDialog)
    frame = wx.Frame(None, title="w19-hostkey")
    try:
        from hpc_gui.wx_connection import build_connection_panel as build

        monkeypatch.setattr("hpc_gui.wx_connection.load_profiles", lambda: _profiles())
        host = build(frame, profiles=_profiles())
        model = host._wx_connection_model
        box = {}

        def worker():
            box["decision"] = model.decide_host_key(
                HostKeyRequest("lab.example", "SHA256:abc", "target", "ssh-ed25519")
            )

        thread = threading.Thread(target=worker)
        thread.start()
        _pump(wx_app, lambda: "decision" in box, timeout=10)
        thread.join(timeout=10)
        assert box["decision"] == "once"
        assert created_on_main["ident"] == main_ident
    finally:
        frame.Destroy()


# ---------------------------------------------------------------------------
# GUI: transport-loss indicator (CONN-005/CONN-008)
# ---------------------------------------------------------------------------


def test_transport_loss_updates_panel_indicator(wx_app, monkeypatch):
    """REQ CONN-005/008: dead transport leaves CONNECTED with FAILED status."""
    ssh = FakeSsh()
    frame, host, controls, model, messages = _build_panel(
        wx_app, monkeypatch, connect=lambda profile: _fake_session(ssh=ssh)
    )
    try:
        assert host._wx_connection_connect_selected() is True
        _pump(wx_app, lambda: model.controller.state == ConnectionState.CONNECTED)
        live_cb = _controller_disconnect_cb(model, lambda: ssh)
        live_cb("network cable pulled: unit-proof")
        _pump(wx_app, lambda: model.controller.state == ConnectionState.FAILED)
        _pump(wx_app, lambda: controls["status"].GetLabel() != "")
        assert model.controller.session is None
    finally:
        frame.Destroy()

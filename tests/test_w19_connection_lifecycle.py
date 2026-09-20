"""W19 — Connection/session lifecycle and profile switching.

REQ: HPC-W05-CONN-001..020, HPC-W05-RECON-001..007
TODO: HPC-W05-TODO-SHELL-NAV-001/002, HPC-W05-TODO-SHELL-TABS-001/002,
      HPC-W05-TODO-006, HPC-W02-TODO-002, HPC-W05-TODO-007
DEF: DEF-W19-001 (mid-connect Cancel), DEF-W19-002 (off-thread modal),
     DEF-W19-003 (stale transport-loss callback), DEF-W19-004 (no Disconnect
     control / dead-session reuse), DEF-W19-005 (NAV detached instead of
     embedded page).
CON: behavioral assertions on live controller/model/panel/shell objects.
NEG: cancel/reject/failure/transport-loss/stale-callback paths.
Mock boundary: transport (FakeSsh/fake connect_fn) and dialog chrome only;
controller/i18n/panel/shell/session-state are real.
"""

import threading
import time

import pytest

wx = pytest.importorskip("wx")

pytestmark = [pytest.mark.gui, pytest.mark.wx]

from hpc_gui.services.connection_controller import (
    ConnectionController,
    ConnectionState,
    HostKeyRequest,
    close_session,
)
from hpc_gui.wx_connection import (
    WxConnectionModel,
    _controller_disconnect_cb,
    _invoke_on_gui_thread,
    build_connection_panel,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


class FakeSsh:
    def __init__(self):
        self.closed = 0
        self.sent = []
        self._wx_output_subscribers = []

    def close(self):
        self.closed += 1

    def send_shell_input(self, payload):
        self.sent.append(payload)

    def resize_shell_pty(self, columns, rows):
        pass


def _attached_ssh(panel):
    """Renderer-agnostic attached transport (TextCtrl vs WebView panel)."""
    ssh = getattr(panel, "_terminal_ssh", None)
    if ssh is not None:
        return ssh
    return getattr(panel, "_ssh", None)


def _send_path(panel):
    model = getattr(panel, "_terminal_model", None)
    if model is not None and getattr(model, "_send_input", None) is not None:
        return model._send_input
    return getattr(panel, "_send_input", None)


def _fake_session(name="lab", ssh=None):
    ssh = ssh if ssh is not None else FakeSsh()
    return {
        "connected": True,
        "ssh": ssh,
        "profile_name": name,
        "profile": {"name": name, "id": f"id-{name}"},
    }


def _pump(app, predicate, timeout=5):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.ProcessPendingEvents()
        if predicate():
            return
        wx.MilliSleep(2)
    app.ProcessPendingEvents()
    assert predicate()


@pytest.fixture
def wx_app():
    app = wx.App.Get()
    if app is None:
        app = wx.App(False)
    yield app
    for window in wx.GetTopLevelWindows():
        try:
            window.Close()
        except Exception:
            pass
    for _ in range(5):
        try:
            wx.Yield()
        except Exception:
            app.ProcessPendingEvents()
    for window in wx.GetTopLevelWindows():
        try:
            if not window.IsBeingDeleted():
                window.Destroy()
        except Exception:
            pass
    for _ in range(5):
        try:
            wx.Yield()
        except Exception:
            app.ProcessPendingEvents()
    # NOTE: no app.Destroy() here on purpose. Destroying the shared wx.App
    # while shell frames with WebView-backed terminal panels are still
    # draining their deferred deletes crashes the interpreter on shutdown
    # (0xC0000374) after an otherwise green run. Windows are closed and
    # destroyed above; the process exit reclaims the app.


def _profiles():
    return [{"name": "lab", "host": "127.0.0.1", "port": 2222, "username": "tester"}]


def _build_panel(wx_app, monkeypatch, *, connect=None, on_connected=None, on_disconnected=None):
    monkeypatch.setattr("hpc_gui.wx_connection.load_profiles", lambda: _profiles())
    messages = []
    monkeypatch.setattr(wx, "MessageBox", lambda *a, **k: messages.append(a) or wx.ID_OK)
    frame = wx.Frame(None, title="w19")
    host = build_connection_panel(
        frame,
        profiles=_profiles(),
        connect=connect,
        on_connected=on_connected,
        on_disconnected=on_disconnected,
    )
    controls = host._wx_connection_controls
    model = host._wx_connection_model
    controls["choices"].SetSelection(0)
    model.select("lab")
    return frame, host, controls, model, messages


# ---------------------------------------------------------------------------
# unit: supersede / cancel-safe / stale-drop / generation (headless)
# ---------------------------------------------------------------------------


def test_repeated_connect_supersedes_without_conflict():
    """REQ CONN-002: second connect closes the first session, no conflict."""
    first_ssh, second_ssh = FakeSsh(), FakeSsh()
    calls = []

    def fake_connect(profile):
        calls.append(profile["name"])
        return _fake_session(ssh=first_ssh if len(calls) == 1 else second_ssh)

    model = WxConnectionModel(_profiles(), connect=fake_connect)
    assert model.select("lab")
    assert model.connect_selected() is True
    first = model.controller.session
    assert model.controller.state == ConnectionState.CONNECTED
    assert model.connect_selected() is True
    second = model.controller.session
    assert first_ssh.closed == 1
    assert second is not first
    assert second["session_generation"] != first["session_generation"]
    assert model.controller.state == ConnectionState.CONNECTED


def test_model_cancel_while_connecting_returns_to_safe_state():
    """REQ CONN-003 / DEF-W19-001: cancel before worker returns drops session."""
    ssh = FakeSsh()
    model = WxConnectionModel(_profiles(), connect=lambda profile: _fake_session(ssh=ssh))
    assert model.select("lab")
    model.controller.begin_connect()
    model.controller.cancel_token.set()
    # Simulate the worker finishing after the user cancelled.
    session = model._connect(dict(_profiles()[0]))
    model.controller.cancel_connect()
    close_session(session)
    assert model.controller.state == ConnectionState.DISCONNECTED
    assert model.controller.session is None
    assert ssh.closed == 1


def test_stale_transport_callback_cannot_fail_new_session():
    """REQ RECON-006/007 / DEF-W19-003: old transport death is dropped."""
    ssh_a, ssh_b = FakeSsh(), FakeSsh()
    model = WxConnectionModel(_profiles(), connect=lambda profile: _fake_session())
    model.controller.finish(_fake_session(ssh=ssh_a))
    stale_cb = _controller_disconnect_cb(model, lambda: ssh_a)
    # Reconnect supersedes with a fresh session identity.
    model.controller.finish(_fake_session(ssh=ssh_b))
    stale_cb("transport lost")
    assert model.controller.state == ConnectionState.CONNECTED
    assert model.controller.session["ssh"] is ssh_b


def test_matching_transport_callback_fails_and_invalidates():
    """REQ CONN-005: live transport loss leaves CONNECTED and notifies shell."""
    ssh = FakeSsh()
    invalidated = []
    model = WxConnectionModel(_profiles(), connect=lambda profile: _fake_session())
    model._session_invalidated_hook = lambda: invalidated.append(True)
    model.controller.finish(_fake_session(ssh=ssh))
    live_cb = _controller_disconnect_cb(model, lambda: ssh)
    live_cb("transport lost")
    assert model.controller.state == ConnectionState.FAILED
    assert model.controller.session is None
    assert invalidated == [True]


def test_transport_callback_without_live_session_is_dropped():
    """REQ CONN-002: callback during CONNECTING must not corrupt the attempt."""
    model = WxConnectionModel(_profiles(), connect=lambda profile: _fake_session())
    model.controller.begin_connect()
    cb = _controller_disconnect_cb(model, lambda: None)
    cb("transport lost")
    assert model.controller.state == ConnectionState.CONNECTING


def test_reconnect_mints_fresh_session_identity():
    """REQ CONN-006 / RECON-007: every finish carries a new generation."""
    controller = ConnectionController()
    controller.finish(_fake_session())
    first = controller.session["session_generation"]
    controller.finish(_fake_session())
    second = controller.session["session_generation"]
    assert isinstance(first, int) and isinstance(second, int) and second != first


def test_close_session_is_best_effort():
    """CON lifecycle: teardown never raises on odd inputs."""

    class Exploding:
        def close(self):
            raise RuntimeError("boom")

    close_session(None)
    close_session({"ssh": None})
    close_session({"ssh": Exploding()})
    close_session("not-a-session")


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


# ---------------------------------------------------------------------------
# GUI: shell tab order / NAV routing / keyboard+focus (SHELL-* TODOs)
# ---------------------------------------------------------------------------


CANONICAL_TAB_ORDER = (
    "APP-CONNECT",
    "NAV-TERMINAL",
    "NAV-JOBS",
    "NAV-DIRECTORIES",
    "NAV-FILES",
    "NAV-EDITOR",
    "NAV-LOGS",
)


def _build_shell(wx_app):
    from hpc_gui.wx_shell import create_shell_frame

    frame, lifecycle, session_state = create_shell_frame(wx_app)
    frame.Show()
    wx_app.ProcessPendingEvents()
    return frame, lifecycle, session_state


def test_shell_tab_order_is_canonical(wx_app):
    """TODO SHELL-NAV-001: one frozen main-tab order."""
    from hpc_gui.wx_shell import create_shell_frame

    frame, _, _ = create_shell_frame(wx_app)
    try:
        frame.Show()
        wx_app.ProcessPendingEvents()
        notebook = frame._wx_shell_controls["notebook"]
        pages = frame._wx_shell_controls["pages"]
        assert notebook.GetPageCount() == len(CANONICAL_TAB_ORDER)
        indices = [notebook.FindPage(pages[key]["page"]) for key in CANONICAL_TAB_ORDER]
        assert indices == sorted(indices)
        assert len(set(indices)) == len(indices)
    finally:
        frame.Destroy()


def test_nav_actions_route_to_embedded_pages(wx_app):
    """TODO SHELL-NAV-002: NAV-* selects the existing embedded page."""
    from hpc_gui.wx_shell import _dispatch

    frame, lifecycle, session_state = _build_shell(wx_app)
    try:
        notebook = frame._wx_shell_controls["notebook"]
        pages = frame._wx_shell_controls["pages"]
        before = len(wx.GetTopLevelWindows())
        for key in ("NAV-TERMINAL", "NAV-JOBS", "NAV-DIRECTORIES", "NAV-FILES", "NAV-EDITOR", "NAV-LOGS", "APP-CONNECT"):
            _dispatch(key, frame, lifecycle, session_state)
            wx_app.ProcessPendingEvents()
            assert notebook.GetSelection() == notebook.FindPage(pages[key]["page"]), key
        assert len(wx.GetTopLevelWindows()) == before
    finally:
        frame.Destroy()


def test_keyboard_tab_navigation_and_focus_restoration(wx_app):
    """TODO SHELL-TABS-001/002: tabs reachable, selection + focus deterministic."""
    from hpc_gui.wx_shell import _dispatch

    frame, lifecycle, session_state = _build_shell(wx_app)
    try:
        notebook = frame._wx_shell_controls["notebook"]
        pages = frame._wx_shell_controls["pages"]
        count = notebook.GetPageCount()
        assert count == len(CANONICAL_TAB_ORDER)
        for index in list(range(count)) + [0, count - 1]:
            notebook.SetSelection(index)
            wx_app.ProcessPendingEvents()
            assert notebook.GetSelection() == index
        _dispatch("NAV-TERMINAL", frame, lifecycle, session_state)
        wx_app.ProcessPendingEvents()
        terminal_page = pages["NAV-TERMINAL"]["page"]
        assert notebook.GetSelection() == notebook.FindPage(terminal_page)
        focus = wx.Window.FindFocus()
        assert focus is not None
        ancestor = focus
        while ancestor is not None and ancestor is not terminal_page:
            ancestor = ancestor.GetParent()
        assert ancestor is terminal_page
    finally:
        frame.Destroy()


# ---------------------------------------------------------------------------
# session rebinding across reconnect / profile switch
# ---------------------------------------------------------------------------


def test_reconnect_rebinds_all_domains_through_canonical_session(wx_app):
    """REQ CONN-010..014: terminal/jobs/remote see the new canonical session."""
    from hpc_gui.wx_shell import _connection_callbacks
    from hpc_gui.wx_lifecycle import WxLifecycleController

    frame, lifecycle_state, session_state = _build_shell(wx_app)
    lifecycle = WxLifecycleController()
    try:
        cbs = _connection_callbacks(session_state, frame, lifecycle)
        ssh_a, ssh_b = FakeSsh(), FakeSsh()
        session_a = _fake_session(name="lab-a", ssh=ssh_a)
        session_b = _fake_session(name="lab-b", ssh=ssh_b)
        cbs["on_connected"](session_a)
        terminal = session_state.get("_embedded_terminal_panel")
        assert terminal is not None
        assert _attached_ssh(terminal) is ssh_a
        cbs["on_connected"](session_b)
        assert session_state["session"] is session_b
        assert _attached_ssh(terminal) is ssh_b
        assert session_state["generation"] >= 2
    finally:
        frame.Destroy()


def test_profile_switch_invalidates_navigation_and_filters():
    """TODO HPC-W02-TODO-002: stores/filters follow the new profile."""
    from hpc_gui.services.remote_navigation_store import navigation_store_for_profile
    from hpc_gui.wx_shell import _remote_files_callbacks

    store_a = navigation_store_for_profile("profile-alpha")
    store_b = navigation_store_for_profile("profile-beta")
    assert store_a is not store_b
    session_state = {"session": None, "generation": 0}

    def filters_for(profile_id, file_filters):
        session_state["session"] = {
            "profile": {"id": profile_id, "file_filters": file_filters},
            "files": object(),
        }
        cbs = _remote_files_callbacks(session_state, None, None)
        return cbs["provider_filters"](), cbs["navigation_store"]()

    filters_a, resolved_a = filters_for("profile-alpha", ["*.out"])
    filters_b, resolved_b = filters_for("profile-beta", ["*.log"])
    assert tuple(filters_a) == ("*.out",)
    assert tuple(filters_b) == ("*.log",)
    assert resolved_a is store_a
    assert resolved_b is store_b

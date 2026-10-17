"""W19 connection model and session lifecycle acceptance tests."""

from w19_connection_support import FakeSsh, _fake_session, _profiles
from hpc_gui.services.connection_controller import (
    ConnectionController, ConnectionState, close_session,
)
from hpc_gui.wx_connection import (
    WxConnectionModel, _controller_disconnect_cb,
)


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

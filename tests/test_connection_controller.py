from hpc_gui.services.connection_controller import (
    ConnectionController, ConnectionState, HostKeyRequest,
    KeyboardInteractiveRequest, wipe_secret,
)


def test_connection_states_cancel_and_cleanup():
    states = []
    controller = ConnectionController(states.append)
    controller.begin_connect()
    controller.begin_authentication()
    controller.finish({"connected": True})
    assert controller.state is ConnectionState.CONNECTED
    controller.begin_disconnect()
    controller.finish_disconnect()
    assert controller.state is ConnectionState.DISCONNECTED and controller.session is None
    assert states == [ConnectionState.CONNECTING, ConnectionState.AUTHENTICATING, ConnectionState.CONNECTED, ConnectionState.DISCONNECTING, ConnectionState.DISCONNECTED]
    controller.begin_connect()
    controller.cancel_connect()
    assert controller.cancel_token.is_set() and controller.state is ConnectionState.DISCONNECTED


def test_host_key_mfa_jump_requests_are_framework_neutral():
    host_key = HostKeyRequest("cluster", "SHA256:fingerprint", "jump")
    mfa = KeyboardInteractiveRequest("MFA", "Code required", ("Code:",))
    assert host_key.role == "jump" and mfa.prompts == ("Code:",)


def test_secret_cleanup_and_no_qt_import():
    secret = bytearray(b"secret")
    wipe_secret(secret)
    assert secret == bytearray(6)
    source = __import__("inspect").getsource(ConnectionController)
    assert "PySide" not in source

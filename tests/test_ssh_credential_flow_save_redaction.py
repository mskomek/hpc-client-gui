"""SSH credential-flow regression tests (SSH-1 .. SSH-12).

The original regression: Save & Connect cleared the typed password before the
connection attempt when "remember password" was off, so Paramiko received no
credential and raised "No authentication methods available". These tests
assert the actual credential crossing each boundary and the absence of
persisted/leaked secrets, not just that a callback returned True.
"""

from __future__ import annotations

pytest_plugins = ('support.test_ssh_credential_flow_shared',)
from support.test_ssh_credential_flow_shared import (
    ConnectionDialog,
    LOGIN,
    LoginWidget,
    NoAuthenticationCredentialError,
    SSHConnInfo,
    _PasswordSource,
    _capture_begin_connect,
    _connect_with_error,
    _profile,
    describe_connection_error,
    mock,
    paramiko,
    pytest,
)

@pytest.mark.unit
def test_ssh_12_secret_never_appears_in_reprs():
    info = SSHConnInfo(host="h", port=22, username="alice", password="secret")
    assert "secret" not in repr(info)
    source = _PasswordSource("alice", lambda: "secret")
    assert "secret" not in repr(source)

@pytest.mark.unit
def test_no_credential_failure_is_classified_distinctly(monkeypatch):
    error = paramiko.SSHException("No authentication methods available")
    info = SSHConnInfo(host="h", port=22, username="alice")
    raised = _connect_with_error(monkeypatch, error, info)
    assert isinstance(raised, NoAuthenticationCredentialError)
    assert isinstance(raised.__cause__, paramiko.SSHException)

    with mock.patch("hpc_gui.core.ui_errors.t", side_effect=lambda key: key):
        message = describe_connection_error(raised, str(raised))
    assert "connection.error_no_credential" in message
    assert "connection.error_authentication" not in message

@pytest.mark.unit
def test_rejected_credential_is_not_reclassified(monkeypatch):
    error = paramiko.AuthenticationException("Authentication failed.")
    info = SSHConnInfo(host="h", port=22, username="alice", password="wrong")
    raised = _connect_with_error(monkeypatch, error, info)
    assert not isinstance(raised, NoAuthenticationCredentialError)
    assert isinstance(raised, paramiko.AuthenticationException)

@pytest.mark.gui
@pytest.mark.qt
def test_save_and_connect_dialog_invokes_exactly_one_save_callback(qt_app):
    saved: list[dict] = []
    connected: list[dict] = []
    dialog = ConnectionDialog(
        on_save=lambda profile: saved.append(profile) or True,
        on_connect=lambda profile: connected.append(profile) or True,
    )
    try:
        dialog.profile_name.setText("lab")
        dialog.host.setText("cluster.example")
        dialog._save_and_connect_clicked()
        assert len(connected) == 1
        assert saved == []
    finally:
        dialog.deleteLater()

@pytest.mark.gui
@pytest.mark.qt
def test_save_and_connect_dialog_falls_back_to_save_handler(qt_app):
    saved: list[dict] = []
    dialog = ConnectionDialog(on_save=lambda profile: saved.append(profile) or True)
    try:
        dialog.profile_name.setText("lab")
        dialog.host.setText("cluster.example")
        dialog._save_and_connect_clicked()
        assert len(saved) == 1
    finally:
        dialog.deleteLater()

@pytest.mark.gui
@pytest.mark.qt
def test_one_logical_save_emits_one_canonical_event(qt_app, monkeypatch):
    login = LoginWidget()
    try:
        _capture_begin_connect(login, monkeypatch)
        console_lines: list[str] = []
        login.console_message.connect(console_lines.append)
        with (
            mock.patch(f"{LOGIN}.load_profiles", return_value=[]),
            mock.patch(f"{LOGIN}.upsert_profile") as upsert,
            mock.patch(f"{LOGIN}.append_event") as append_event,
        ):
            assert login._save_and_connect_from_dialog(
                _profile(password="secret", save_password=False)
            ) is True
        assert upsert.call_count == 1
        save_events = [
            call for call in append_event.call_args_list
            if call.args and call.args[0].get("type") == "profile_save"
        ]
        assert len(save_events) == 1
        saved_lines = [line for line in console_lines if "lab" in line]
        assert len(saved_lines) == 1
    finally:
        login.deleteLater()

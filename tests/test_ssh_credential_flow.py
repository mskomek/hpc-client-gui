"""SSH credential-flow regression tests (SSH-1 .. SSH-12).

The original regression: Save & Connect cleared the typed password before the
connection attempt when "remember password" was off, so Paramiko received no
credential and raised "No authentication methods available". These tests
assert the actual credential crossing each boundary and the absence of
persisted/leaked secrets, not just that a callback returned True.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest import mock

import paramiko
import pytest
from PySide6.QtWidgets import QApplication

from hpc_gui.config.models import SSHConfig
from hpc_gui.core.ui_errors import describe_connection_error
from hpc_gui.services.connection_profile_service import normalize_auth_methods
from hpc_gui.ssh.client import (
    NoAuthenticationCredentialError,
    SSHClientWrapper,
    SSHConnInfo,
    _ConnectionAuthStrategy,
    _KeyboardInteractiveSource,
    _PasswordSource,
)
from hpc_gui.ui.dialogs.connection_dialog import ConnectionDialog
from hpc_gui.ui.widgets.login_widget import LoginWidget, _ConnectionWorker

LOGIN = "hpc_gui.ui.widgets.login_widget"


@pytest.fixture(scope="module")
def qt_app():
    app = QApplication.instance() or QApplication([])
    from hpc_gui.core.i18n import load_language

    load_language("en")
    yield app


def _profile(**overrides) -> dict:
    profile = {
        "name": "lab",
        "host": "cluster.example",
        "port": 22,
        "username": "alice",
        "password": "",
        "save_password": False,
        "password_prompt_policy": "when-needed",
        "key_path": "",
        "system": {},
        "file_manager": {},
        "jump_host": {},
    }
    profile.update(overrides)
    return profile


def _capture_begin_connect(login: LoginWidget, monkeypatch) -> dict:
    captured: dict = {}

    def fake_begin(cfg, old_ssh):
        captured["cfg"] = cfg
        return True

    monkeypatch.setattr(login, "_begin_connect_async", fake_begin)
    return captured


def _secret_keys(profile: dict) -> dict:
    return {
        key: profile.get(key)
        for key in ("password", "password_keychain_ref", "password_dpapi", "password_enc", "password_salt")
        if key in profile
    }


# ---------------------------------------------------------------------------
# SSH-1: Save & Connect, password NOT saved
# ---------------------------------------------------------------------------


@pytest.mark.gui
@pytest.mark.qt
def test_ssh_1_save_and_connect_uses_typed_password_without_persisting(qt_app, monkeypatch):
    login = LoginWidget()
    try:
        captured = _capture_begin_connect(login, monkeypatch)
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

        assert captured["cfg"].password == "secret"
        saved = upsert.call_args.args[0]
        assert _secret_keys(saved) == {"password": ""}
        assert upsert.call_count == 1
        save_events = [
            call for call in append_event.call_args_list
            if call.args and call.args[0].get("type") == "profile_save"
        ]
        assert len(save_events) == 1
        # SSH-12: the transient secret never reaches console/history.
        history = json.dumps([call.args[0] for call in append_event.call_args_list])
        assert "secret" not in history
        assert "secret" not in "\n".join(console_lines)
    finally:
        login.deleteLater()


# ---------------------------------------------------------------------------
# SSH-2: Save & Connect with saved password uses approved secure storage
# ---------------------------------------------------------------------------


@pytest.mark.gui
@pytest.mark.qt
def test_ssh_2_save_and_connect_saved_password_uses_secure_store(qt_app, monkeypatch):
    login = LoginWidget()
    try:
        captured = _capture_begin_connect(login, monkeypatch)
        with (
            mock.patch(f"{LOGIN}.load_profiles", return_value=[]),
            mock.patch(f"{LOGIN}.upsert_profile") as upsert,
            mock.patch(f"{LOGIN}.append_event"),
            mock.patch(f"{LOGIN}.keychain_available", return_value=True),
            mock.patch(f"{LOGIN}.protect_keychain_secret", return_value="kc-ref") as protect,
            mock.patch(f"{LOGIN}.delete_keychain_secret"),
        ):
            assert login._save_and_connect_from_dialog(
                _profile(password="secret", save_password=True)
            ) is True

        protect.assert_called_once_with("secret", None)
        saved = upsert.call_args.args[0]
        assert saved["password_keychain_ref"] == "kc-ref"
        assert saved["password"] == ""
        assert captured["cfg"].password == "secret"
    finally:
        login.deleteLater()


# ---------------------------------------------------------------------------
# SSH-3: Save only, password not saved
# ---------------------------------------------------------------------------


@pytest.mark.gui
@pytest.mark.qt
def test_ssh_3_save_only_does_not_connect_and_does_not_persist(qt_app, monkeypatch):
    login = LoginWidget()
    try:
        captured = _capture_begin_connect(login, monkeypatch)
        login._load_profile_into_fields(_profile(save_password=False))
        login.password.setText("secret")
        with (
            mock.patch(f"{LOGIN}.load_profiles", return_value=[]),
            mock.patch(f"{LOGIN}.upsert_profile") as upsert,
            mock.patch(f"{LOGIN}.append_event"),
        ):
            assert login.save_profile() is True

        assert "cfg" not in captured
        saved = upsert.call_args.args[0]
        assert _secret_keys(saved) == {"password": ""}
    finally:
        login.deleteLater()


# ---------------------------------------------------------------------------
# SSH-4: Existing secure password resolves and reaches SSH
# ---------------------------------------------------------------------------


@pytest.mark.gui
@pytest.mark.qt
def test_ssh_4_existing_saved_secret_reaches_ssh(qt_app, monkeypatch):
    login = LoginWidget()
    try:
        captured = _capture_begin_connect(login, monkeypatch)
        stored = _profile(save_password=True, password_dpapi="token")
        login._load_profile_into_fields(stored)
        with (
            mock.patch(f"{LOGIN}.load_profiles", return_value=[stored]),
            mock.patch(f"{LOGIN}.unprotect_secret", return_value="saved-secret") as unprotect,
            mock.patch(f"{LOGIN}.QInputDialog.getText", side_effect=AssertionError("no prompt")),
        ):
            assert login.connect_clicked() is True

        unprotect.assert_called_once_with("token")
        assert captured["cfg"].password == "saved-secret"
    finally:
        login.deleteLater()


# ---------------------------------------------------------------------------
# SSH-5 / SSH-6: missing credential prompts; cancellation aborts
# ---------------------------------------------------------------------------


@pytest.mark.gui
@pytest.mark.qt
def test_ssh_5_profile_without_saved_password_prompts_and_uses_transient(qt_app, monkeypatch):
    login = LoginWidget()
    try:
        captured = _capture_begin_connect(login, monkeypatch)
        stored = _profile(save_password=False)
        login._load_profile_into_fields(stored)
        with (
            mock.patch(f"{LOGIN}.load_profiles", return_value=[stored]),
            mock.patch(f"{LOGIN}.upsert_profile") as upsert,
            mock.patch(f"{LOGIN}.QInputDialog.getText", return_value=("typed", True)),
        ):
            assert login.connect_clicked() is True

        assert captured["cfg"].password == "typed"
        assert not upsert.called  # transient prompt result is never persisted
    finally:
        login.deleteLater()


@pytest.mark.gui
@pytest.mark.qt
def test_ssh_6_prompt_cancellation_aborts_without_ssh(qt_app, monkeypatch):
    login = LoginWidget()
    try:
        captured = _capture_begin_connect(login, monkeypatch)
        stored = _profile(save_password=False)
        login._load_profile_into_fields(stored)
        with (
            mock.patch(f"{LOGIN}.load_profiles", return_value=[stored]),
            mock.patch(f"{LOGIN}.QInputDialog.getText", return_value=("", False)),
        ):
            assert login.connect_clicked() is False

        assert "cfg" not in captured
    finally:
        login.deleteLater()


# ---------------------------------------------------------------------------
# SSH-7: key-only auth never triggers a password prompt
# ---------------------------------------------------------------------------


@pytest.mark.gui
@pytest.mark.qt
def test_ssh_7_key_only_profile_never_prompts(qt_app, monkeypatch):
    login = LoginWidget()
    try:
        captured = _capture_begin_connect(login, monkeypatch)
        stored = _profile(key_path="/home/alice/.ssh/id_ed25519")
        login._load_profile_into_fields(stored)
        with (
            mock.patch(f"{LOGIN}.load_profiles", return_value=[stored]),
            mock.patch(f"{LOGIN}.QInputDialog.getText", side_effect=AssertionError("no prompt")),
        ):
            assert login.connect_clicked() is True

        assert captured["cfg"].key_path == "/home/alice/.ssh/id_ed25519"
        assert captured["cfg"].password == ""
    finally:
        login.deleteLater()


@pytest.mark.gui
@pytest.mark.qt
def test_ssh_7b_password_only_provider_prompts_but_key_provider_does_not(qt_app, monkeypatch):
    login = LoginWidget()
    try:
        def methods(*values):
            return {"provider_template": {"access": {"auth_methods": list(values)}}}

        login._profile_system_settings = methods("password")
        assert login._should_prompt_for_password(None) is True
        login._profile_system_settings = methods("publickey")
        assert login._should_prompt_for_password(None) is False
        login._profile_system_settings = methods("keyboard-interactive")
        assert login._should_prompt_for_password(None) is False
        login._profile_system_settings = methods("password", "keyboard-interactive")
        assert login._should_prompt_for_password(None) is False
        login._profile_system_settings = methods()
        assert login._should_prompt_for_password({"key_path": "/k"}) is False
        login._password_prompt_policy = "edit-only"
        assert login._should_prompt_for_password(None) is False
    finally:
        login.deleteLater()


# ---------------------------------------------------------------------------
# SSH-8: agent / look_for_keys survive the custom auth strategy
# ---------------------------------------------------------------------------


class _FakeAgent:
    def __init__(self, keys):
        self._keys = keys

    def get_keys(self):
        return self._keys


@pytest.mark.unit
def test_ssh_8_custom_strategy_preserves_agent_and_key_discovery(monkeypatch):
    agent_key = object()
    monkeypatch.setattr(
        "hpc_gui.ssh.client.paramiko.Agent", lambda: _FakeAgent([agent_key])
    )
    discovered = object()
    on_disk = paramiko.auth_strategy.OnDiskPrivateKey(
        "alice", "implicit-home", Path("/home/alice/.ssh/id_ed25519"), discovered
    )
    monkeypatch.setattr(
        "hpc_gui.ssh.client._discoverable_key_sources",
        lambda username, password: iter([on_disk]),
    )
    info = SSHConnInfo(
        host="h",
        port=22,
        username="alice",
        password="pw",
        keyboard_interactive_handler=lambda *a: [],
    )
    sources = list(_ConnectionAuthStrategy(info).get_sources())
    kinds = [type(source) for source in sources]
    assert paramiko.auth_strategy.InMemoryPrivateKey in kinds  # agent key
    assert paramiko.auth_strategy.OnDiskPrivateKey in kinds
    assert _PasswordSource in kinds
    assert _KeyboardInteractiveSource in kinds

    # Opt-outs are honored too.
    info_no_agent = SSHConnInfo(
        host="h",
        port=22, username="alice", allow_agent=False, look_for_keys=False
    )
    sources = list(_ConnectionAuthStrategy(info_no_agent).get_sources())
    assert sources == []


@pytest.mark.unit
def test_ssh_8b_partial_authentication_continues_to_next_source():
    calls: list[str] = []

    class _Transport:
        def auth_publickey(self, username, key):
            calls.append("publickey")
            return ["password"]  # partial: server wants a second factor

        def auth_password(self, username, password):
            calls.append("password")
            return []

    info = SSHConnInfo(
        host="h",
        port=22, username="alice", password="pw", allow_agent=False, look_for_keys=False
    )
    strategy = _ConnectionAuthStrategy(info, pkey=object())
    result = strategy.authenticate(_Transport())
    assert calls == ["publickey", "password"]
    assert len(result) == 2


@pytest.mark.unit
def test_ssh_8c_connect_paths_forward_agent_and_key_flags(monkeypatch):
    import hpc_gui.ssh.client as client_module

    recorded: list[dict] = []

    class _Client:
        def __init__(self):
            self.transport = None

        def load_system_host_keys(self):
            pass

        def set_missing_host_key_policy(self, policy):
            pass

        def connect(self, **kwargs):
            recorded.append(kwargs)

        def open_sftp(self):
            return object()

        def close(self):
            pass

        def get_transport(self):
            return None

    monkeypatch.setattr(client_module.paramiko, "SSHClient", _Client)
    monkeypatch.setattr(client_module, "app_data_dir", lambda: Path("/tmp"))

    SSHClientWrapper(
        SSHConnInfo(
            host="h", port=22, username="alice", password="pw", allow_agent=False, look_for_keys=False
        )
    ).connect()
    assert recorded[-1]["allow_agent"] is False
    assert recorded[-1]["look_for_keys"] is False


# ---------------------------------------------------------------------------
# SSH-9 / SSH-10 / SSH-11: keyboard-interactive metadata propagation
# ---------------------------------------------------------------------------


def _run_worker(monkeypatch, cfg_kwargs: dict) -> SSHConnInfo:
    from hpc_gui.config.system_profile import normalize_system_settings

    cfg = SSHConfig(
        host="cluster.example",
        port=22,
        username="alice",
        system_settings=normalize_system_settings(cfg_kwargs.pop("system_settings", {})),
        **cfg_kwargs,
    )
    recorded: dict = {}

    class _FakeWrapper:
        def __init__(self, conn, **kwargs):
            recorded["conn"] = conn
            self.info = conn
            self.client = None
            self.sftp = object()

        def connect(self, **kwargs):
            pass

        def close(self):
            pass

    monkeypatch.setattr(f"{LOGIN}.SSHClientWrapper", _FakeWrapper)
    worker = _ConnectionWorker(cfg, (120, 40), lambda msg: None, lambda msg: None)
    worker.run()
    return recorded["conn"]


@pytest.mark.unit
def test_ssh_9_keyboard_interactive_metadata_reaches_conn_info(monkeypatch):
    settings = {
        "provider_template": {"access": {"auth_methods": ["keyboard-interactive"]}}
    }
    conn = _run_worker(monkeypatch, {"system_settings": settings})
    assert conn.keyboard_interactive_handler is not None
    assert normalize_auth_methods(settings) == ("keyboard-interactive",)


@pytest.mark.unit
def test_ssh_10_password_plus_keyboard_interactive_available(monkeypatch):
    settings = {
        "provider_template": {
            "access": {"auth_methods": ["password", "keyboard-interactive"]}
        }
    }
    conn = _run_worker(monkeypatch, {"password": "pw", "system_settings": settings})
    assert conn.password == "pw"
    assert conn.keyboard_interactive_handler is not None
    sources = list(_ConnectionAuthStrategy(conn).get_sources())
    kinds = [type(source) for source in sources]
    assert _PasswordSource in kinds
    assert _KeyboardInteractiveSource in kinds


@pytest.mark.unit
def test_ssh_11_unknown_auth_methods_are_ignored_and_not_executable(monkeypatch):
    settings = {
        "provider_template": {
            "access": {"auth_methods": ["password", "telnet", "exec", "publickey;rm -rf /"]}
        }
    }
    assert normalize_auth_methods(settings) == ("password",)
    conn = _run_worker(monkeypatch, {"system_settings": settings})
    assert conn.keyboard_interactive_handler is None

    legacy = {"access": {"auth_methods": ["keyboard-interactive", "bogus"]}}
    assert normalize_auth_methods(legacy) == ("keyboard-interactive",)


# ---------------------------------------------------------------------------
# SSH-9 legacy provider template conversion
# ---------------------------------------------------------------------------


@pytest.mark.gui
@pytest.mark.qt
def test_ssh_9b_plugin_access_metadata_survives_dialog_to_login_chain(qt_app):
    """Provider access metadata must survive the full Path:
    plugin template -> ConnectionDialog provider_template -> profile -> login
    system settings -> keyboard-interactive handler.
    """
    from hpc_gui.plugins.templates import PluginSystemTemplate

    template = PluginSystemTemplate(
        settings={"name": "TRUBA"},
        provenance={"kind": "plugin", "plugin_id": "org.hpcclient.truba"},
        structured={
            "schema_version": 3,
            "access": {"auth_methods": ["password", "keyboard-interactive"]},
        },
    )
    dialog = ConnectionDialog()
    try:
        dialog._apply_system_template(
            dict(template.settings), dict(template.provenance), dict(template.structured)
        )
        collected = dialog._collect_profile()
    finally:
        dialog.deleteLater()
    assert collected is not None
    assert collected["provider_template"]["access"]["auth_methods"] == [
        "password",
        "keyboard-interactive",
    ]

    login = LoginWidget()
    try:
        login._load_profile_into_fields(collected)
        assert normalize_auth_methods(login._profile_system_settings) == (
            "password",
            "keyboard-interactive",
        )
    finally:
        login.deleteLater()


@pytest.mark.unit
def test_ssh_12_secret_never_appears_in_reprs():
    info = SSHConnInfo(host="h", port=22, username="alice", password="secret")
    assert "secret" not in repr(info)
    source = _PasswordSource("alice", lambda: "secret")
    assert "secret" not in repr(source)


# ---------------------------------------------------------------------------
# Error classification (section 9)
# ---------------------------------------------------------------------------


class _FailingClient:
    def __init__(self, error):
        self._error = error
        self.transport = None

    def load_system_host_keys(self):
        pass

    def load_host_keys(self, path):
        pass

    def set_missing_host_key_policy(self, policy):
        pass

    def connect(self, **kwargs):
        raise self._error

    def close(self):
        pass

    def get_transport(self):
        return None


def _connect_with_error(monkeypatch, error, info: SSHConnInfo):
    import hpc_gui.ssh.client as client_module

    monkeypatch.setattr(
        client_module.paramiko, "SSHClient", lambda: _FailingClient(error)
    )
    monkeypatch.setattr(client_module, "app_data_dir", lambda: Path("/tmp"))
    with pytest.raises(type(error)) as excinfo:
        SSHClientWrapper(info).connect()
    return excinfo.value


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


# ---------------------------------------------------------------------------
# Duplicate profile-save logging (one logical save -> one event)
# ---------------------------------------------------------------------------


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

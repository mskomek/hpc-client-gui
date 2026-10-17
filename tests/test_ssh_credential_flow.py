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
    LOGIN,
    LoginWidget,
    Path,
    SSHClientWrapper,
    SSHConnInfo,
    _ConnectionAuthStrategy,
    _FakeAgent,
    _KeyboardInteractiveSource,
    _PasswordSource,
    _capture_begin_connect,
    _profile,
    _secret_keys,
    json,
    mock,
    paramiko,
    pytest,
)

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

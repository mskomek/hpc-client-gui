from __future__ import annotations

from types import SimpleNamespace

import pytest

from hpc_gui.cli.session import CLIConnectionError, build_ssh_conn_info
from hpc_gui.core.crypto_master import encrypt_with_master


def _profile() -> dict[str, object]:
    encrypted = encrypt_with_master("app-master", "arf-login-password")
    return {
        "name": "arf",
        "host": "arf.example",
        "port": 22,
        "username": "user",
        "cli_allowed": True,
        "save_password": True,
        "password_enc": encrypted.token,
        "password_salt": encrypted.salt,
    }


def _args(**overrides):
    values = {
        "profile": "arf",
        "host": "",
        "port": None,
        "username": "",
        "key_path": "",
        "strict_host_key": False,
        "password_stdin": False,
        "password_prompt": False,
        "no_saved_password": False,
        "timeout": 30,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


@pytest.mark.unit
def test_saved_master_encrypted_profile_password_is_used_in_cli(monkeypatch) -> None:
    profile = _profile()
    monkeypatch.setattr("hpc_gui.cli.session.load_profiles", lambda: [profile])
    monkeypatch.setattr("hpc_gui.services.connection_profile_service.load_profile_by_name", lambda _name: profile)
    monkeypatch.setattr("hpc_gui.cli.session.load_settings", lambda: {})
    monkeypatch.setattr(
        "hpc_gui.cli.session.sys",
        SimpleNamespace(
            stdin=SimpleNamespace(isatty=lambda: True),
            stderr=SimpleNamespace(
                isatty=lambda: True,
                write=lambda _text: None,
                flush=lambda: None,
            ),
        ),
    )
    monkeypatch.setattr("hpc_gui.cli.session.getpass.getpass", lambda prompt: "app-master")

    info = build_ssh_conn_info(_args())

    assert info.password == "arf-login-password"


@pytest.mark.unit
def test_saved_master_encrypted_password_is_available_as_key_passphrase(monkeypatch) -> None:
    profile = _profile()
    profile["key_path"] = "C:\\keys\\arf_ed25519"
    monkeypatch.setattr("hpc_gui.cli.session.load_profiles", lambda: [profile])
    monkeypatch.setattr("hpc_gui.services.connection_profile_service.load_profile_by_name", lambda _name: profile)
    monkeypatch.setattr("hpc_gui.cli.session.load_settings", lambda: {})
    monkeypatch.setattr(
        "hpc_gui.cli.session.sys",
        SimpleNamespace(
            stdin=SimpleNamespace(isatty=lambda: True),
            stderr=SimpleNamespace(isatty=lambda: True),
        ),
    )
    monkeypatch.setattr("hpc_gui.cli.session.getpass.getpass", lambda _prompt: "app-master")

    info = build_ssh_conn_info(_args())

    assert info.password == "arf-login-password"
    assert info.key_path == "C:\\keys\\arf_ed25519"


@pytest.mark.unit
def test_saved_profile_uses_dpapi_cached_master_without_prompt(monkeypatch) -> None:
    profile = _profile()
    monkeypatch.setattr("hpc_gui.cli.session.load_profiles", lambda: [profile])
    monkeypatch.setattr("hpc_gui.services.connection_profile_service.load_profile_by_name", lambda _name: profile)
    monkeypatch.setattr("hpc_gui.cli.session.load_settings", lambda: {"master_password_dpapi": "protected"})
    monkeypatch.setattr("hpc_gui.cli.session.secret_store.is_available", lambda: True)
    monkeypatch.setattr("hpc_gui.cli.session.secret_store.unprotect_secret", lambda _token: "app-master")
    monkeypatch.setattr(
        "hpc_gui.cli.session.getpass.getpass",
        lambda _prompt: pytest.fail("A remembered master password should not prompt"),
    )

    info = build_ssh_conn_info(_args())

    assert info.password == "arf-login-password"


@pytest.mark.unit
def test_saved_profile_password_answers_keyboard_interactive_and_prompts_for_otp(monkeypatch) -> None:
    profile = _profile()
    monkeypatch.setattr("hpc_gui.cli.session.load_profiles", lambda: [profile])
    monkeypatch.setattr("hpc_gui.services.connection_profile_service.load_profile_by_name", lambda _name: profile)
    monkeypatch.setattr("hpc_gui.cli.session.load_settings", lambda: {})
    monkeypatch.setattr(
        "hpc_gui.cli.session.sys",
        SimpleNamespace(
            stdin=SimpleNamespace(isatty=lambda: True),
            stderr=SimpleNamespace(
                isatty=lambda: True,
                write=lambda _text: None,
                flush=lambda: None,
            ),
        ),
    )
    responses = iter(("app-master", "123456"))
    monkeypatch.setattr("hpc_gui.cli.session.getpass.getpass", lambda _prompt: next(responses))

    info = build_ssh_conn_info(_args())

    assert info.keyboard_interactive_handler is not None
    assert info.keyboard_interactive_handler(
        "Authentication", "", [("Password:", False), ("Verification code:", False)]
    ) == ["arf-login-password", "123456"]


@pytest.mark.unit
def test_explicit_ssh_password_prompt_overrides_saved_profile_secret(monkeypatch) -> None:
    profile = _profile()
    monkeypatch.setattr("hpc_gui.cli.session.load_profiles", lambda: [profile])
    monkeypatch.setattr(
        "hpc_gui.cli.session.sys",
        SimpleNamespace(
            stdin=SimpleNamespace(isatty=lambda: True),
            stderr=SimpleNamespace(isatty=lambda: True),
        ),
    )
    monkeypatch.setattr("hpc_gui.cli.session.getpass.getpass", lambda _prompt: "typed-ssh-password")

    info = build_ssh_conn_info(_args(password_prompt=True))

    assert info.password == "typed-ssh-password"


@pytest.mark.unit
def test_saved_profile_secret_requires_interactive_terminal(monkeypatch) -> None:
    profile = _profile()
    monkeypatch.setattr("hpc_gui.cli.session.load_profiles", lambda: [profile])
    monkeypatch.setattr("hpc_gui.services.connection_profile_service.load_profile_by_name", lambda _name: profile)
    monkeypatch.setattr("hpc_gui.cli.session.load_settings", lambda: {})
    monkeypatch.setattr(
        "hpc_gui.cli.session.sys",
        SimpleNamespace(
            stdin=SimpleNamespace(isatty=lambda: False),
            stderr=SimpleNamespace(isatty=lambda: False),
        ),
    )

    with pytest.raises(CLIConnectionError, match="interactive terminal"):
        build_ssh_conn_info(_args())

"""Toolkit independent SSH credential and authentication contracts."""

from __future__ import annotations

from hpc_gui.services.connection_auth_policy import (
    normalize_auth_methods,
    password_prompt_recommended,
)
from hpc_gui.ssh.auth_strategy import _PasswordSource
from hpc_gui.ssh.contracts import SSHConnInfo


def test_ssh_secrets_are_omitted_from_connection_and_auth_source_repr() -> None:
    info = SSHConnInfo(host="cluster", port=22, username="alice", password="secret")
    source = _PasswordSource("alice", lambda: "secret")

    assert "secret" not in repr(info)
    assert "secret" not in repr(source)


def test_auth_metadata_uses_known_unique_methods_only() -> None:
    settings = {
        "provider_template": {
            "access": {
                "auth_methods": [
                    "password",
                    "keyboard-interactive",
                    "exec",
                    "password",
                ]
            }
        }
    }

    assert normalize_auth_methods(settings) == ("password", "keyboard-interactive")


def test_password_prompt_policy_respects_declared_auth_sources() -> None:
    assert not password_prompt_recommended(
        {"access": {"auth_methods": ["publickey"]}}, has_key_path=False
    )
    assert not password_prompt_recommended(
        {"access": {"auth_methods": ["keyboard-interactive"]}},
        has_key_path=False,
    )
    assert password_prompt_recommended(
        {"access": {"auth_methods": ["password"]}}, has_key_path=False
    )

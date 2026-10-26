"""SSH authentication source selection and metadata regressions."""

from __future__ import annotations

from pathlib import Path

import paramiko
import pytest

from hpc_gui.config.models import SSHConfig
from hpc_gui.services.connection_profile_service import normalize_auth_methods
from hpc_gui.ssh.client import (
    SSHClientWrapper,
    SSHConnInfo,
    _ConnectionAuthStrategy,
    _KeyboardInteractiveSource,
    _PasswordSource,
)
from hpc_gui.ui.widgets.login_widget import _ConnectionWorker

LOGIN = "hpc_gui.ui.widgets.login_widget"


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

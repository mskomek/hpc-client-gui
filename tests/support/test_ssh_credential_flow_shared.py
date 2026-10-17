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
class _FakeAgent:
    def __init__(self, keys):
        self._keys = keys

    def get_keys(self):
        return self._keys
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

__all__ = [
    'json',
    'Path',
    'mock',
    'paramiko',
    'pytest',
    'QApplication',
    'SSHConfig',
    'describe_connection_error',
    'normalize_auth_methods',
    'NoAuthenticationCredentialError',
    'SSHClientWrapper',
    'SSHConnInfo',
    '_ConnectionAuthStrategy',
    '_KeyboardInteractiveSource',
    '_PasswordSource',
    'ConnectionDialog',
    'LoginWidget',
    '_ConnectionWorker',
    'LOGIN',
    'qt_app',
    '_profile',
    '_capture_begin_connect',
    '_secret_keys',
    '_FakeAgent',
    '_run_worker',
    '_FailingClient',
    '_connect_with_error',
]

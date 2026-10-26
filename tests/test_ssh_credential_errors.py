"""SSH connection error classification regressions."""

from __future__ import annotations

from pathlib import Path
from unittest import mock

import paramiko
import pytest

from hpc_gui.core.ui_errors import describe_connection_error
from hpc_gui.ssh.client import (
    NoAuthenticationCredentialError,
    SSHClientWrapper,
    SSHConnInfo,
)


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

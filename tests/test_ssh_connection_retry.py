from __future__ import annotations

from unittest.mock import Mock

import pytest

from hpc_gui.config import storage
from hpc_gui.config.storage import get_ssh_connection_attempts, set_ssh_connection_attempts
from hpc_gui.ssh.client import SSHClientWrapper
from hpc_gui.ssh.host_keys import HostKeyRejectedError
from hpc_gui.ssh.retry import retry_connection


@pytest.fixture
def isolated_config(tmp_path, monkeypatch):
    path = tmp_path / "config.json"
    monkeypatch.setattr(storage, "_config_path", lambda: path)
    return path


def test_retry_connection_retries_then_returns(monkeypatch):
    operation = Mock(side_effect=[OSError("temporary"), OSError("temporary"), "connected"])
    messages = []
    monkeypatch.setattr("hpc_gui.ssh.retry.time.sleep", lambda _seconds: None)

    result = retry_connection(operation, attempts=5, on_retry=messages.append)

    assert result == "connected"
    assert operation.call_count == 3
    assert len(messages) == 2


def test_retry_connection_stops_after_configured_attempts(monkeypatch):
    operation = Mock(side_effect=OSError("unreachable"))
    monkeypatch.setattr("hpc_gui.ssh.retry.time.sleep", lambda _seconds: None)

    with pytest.raises(OSError, match="unreachable"):
        retry_connection(operation, attempts=2, on_retry=lambda _message: None)

    assert operation.call_count == 2


def test_host_key_rejection_is_never_retried(monkeypatch):
    operation = Mock(side_effect=HostKeyRejectedError("cluster.example"))
    sleep = Mock()
    monkeypatch.setattr("hpc_gui.ssh.retry.time.sleep", sleep)

    with pytest.raises(HostKeyRejectedError):
        retry_connection(
            operation,
            attempts=5,
            on_retry=lambda _message: None,
            non_retryable=(HostKeyRejectedError,),
        )

    assert operation.call_count == 1
    sleep.assert_not_called()


def test_ssh_wrapper_uses_saved_attempt_count(isolated_config, monkeypatch):
    from hpc_gui.config.storage import update_settings

    update_settings({"ssh_connection_attempts": 3})
    wrapper = SSHClientWrapper()
    connect_once = Mock(side_effect=[OSError("temporary"), None])
    monkeypatch.setattr(wrapper, "_connect_once", connect_once)
    monkeypatch.setattr("hpc_gui.ssh.retry.time.sleep", lambda _seconds: None)

    wrapper.connect()

    assert get_ssh_connection_attempts() == 3
    assert connect_once.call_count == 2


def test_ssh_connection_attempt_setting_is_clamped(isolated_config):
    assert set_ssh_connection_attempts(99) == 5
    assert set_ssh_connection_attempts(0) == 1

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Optional
from unittest import mock
import pytest
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import paramiko  # noqa: E402
from hpc_gui.config.jump_host_profile import (  # noqa: E402
    normalize_jump_host_settings,
)
from hpc_gui.ssh.client import (  # noqa: E402
    HostKeyInfo,
    SSHClientWrapper,
    SSHConnInfo,
    _KnownHostsPolicy,
)
from hpc_gui.ssh.jump import (  # noqa: E402
    JumpAuthenticationError,
    JumpConnection,
    JumpForwardingDeniedError,
    SSHJumpInfo,
    jump_info_from_settings,
)
class _FakeTransport:
    def __init__(self, *, fail_channel: bool = False):
        self.keepalive_calls: list[int] = []
        self.open_channel_calls: list[tuple] = []
        self.fail_channel = fail_channel

    def is_active(self) -> bool:
        return True

    def is_authenticated(self) -> bool:
        return True

    def set_keepalive(self, interval: int) -> None:
        self.keepalive_calls.append(interval)

    def get_banner(self):
        return b""

    def open_channel(self, kind, dest_addr=None, src_addr=None):
        self.open_channel_calls.append((kind, dest_addr, src_addr))
        if self.fail_channel:
            raise paramiko.ChannelException(1, "administratively prohibited")
        return _FakeChannel()
class _FakeChannel:
    def send(self, data: bytes) -> int:
        return len(data)

    def recv(self, size: int) -> bytes:
        return b""

    def settimeout(self, timeout) -> None:
        return None

    def close(self) -> None:
        return None
class _FakeHostKeys:
    def add(self, *args, **kwargs) -> None:
        return None
class _FakeClient:
    """Fake paramiko.SSHClient for either role."""

    def __init__(self, sequence: Optional[list] = None, role: str = "") -> None:
        self.transport = _FakeTransport()
        self.connect_kwargs: dict[str, Any] = {}
        self.policies: list[Any] = []
        self.closed = False
        self.connect_count = 0
        self.sequence = sequence
        self.role = role
        self._host_keys = _FakeHostKeys()
        self.connect_error: Optional[BaseException] = None
        self.sftp_error: Optional[BaseException] = None

    # host-key plumbing
    def load_system_host_keys(self) -> None:
        pass

    def load_host_keys(self, path) -> None:
        pass

    def get_host_keys(self):
        return self._host_keys

    def save_host_keys(self, path) -> None:
        pass

    def set_missing_host_key_policy(self, policy) -> None:
        self.policies.append(policy)

    def open_sftp(self):
        if self.sftp_error is not None:
            raise self.sftp_error
        return _FakeSFTP()

    def connect(self, **kwargs) -> None:
        if self.sequence is not None:
            self.sequence.append(f"{self.role}-connect")
        self.connect_count += 1
        self.connect_kwargs.update(kwargs)
        if self.connect_error is not None:
            raise self.connect_error

    def get_transport(self):
        return None if self.closed else self.transport

    def close(self) -> None:
        self.closed = True
class _FakeSFTP:
    def get_channel(self):
        return _FakeChannel()

    def close(self):
        pass
def make_connected_wrapper(jump_info: Optional[SSHJumpInfo] = None, **info_kwargs):
    """Build a wrapper whose paramiko clients are fakes; returns (w, target, jump).

    ``client.py`` and ``jump.py`` share one ``paramiko`` module object, so a
    single ordered factory hands out the target client first and the jump
    client second.
    """
    sequence: list[str] = []
    target_client = _FakeClient(sequence=sequence, role="target")
    jump_client = _FakeClient(sequence=sequence, role="jump") if jump_info else None
    info = SSHConnInfo(
        host="cluster.example.org",
        port=22,
        username="user",
        keepalive_interval_seconds=30,
        jump=jump_info,
        **info_kwargs,
    )
    wrapper = SSHClientWrapper(info)
    pending = [target_client] + ([jump_client] if jump_client else [])

    def factory(*args, **kwargs):
        return pending.pop(0) if len(pending) > 1 else pending[0]

    with mock.patch(
        "hpc_gui.ssh.client.paramiko.SSHClient", side_effect=factory
    ), mock.patch.object(
        SSHClientWrapper, "_start_shell_session", lambda self: None
    ):
        wrapper.connect()
    return wrapper, target_client, jump_client, sequence
if __name__ == "__main__":
    unittest.main()

__all__ = [
    'os',
    'sys',
    'tempfile',
    'unittest',
    'Path',
    'Any',
    'Optional',
    'mock',
    'pytest',
    'paramiko',
    'normalize_jump_host_settings',
    'HostKeyInfo',
    'SSHClientWrapper',
    'SSHConnInfo',
    '_KnownHostsPolicy',
    'JumpAuthenticationError',
    'JumpConnection',
    'JumpForwardingDeniedError',
    'SSHJumpInfo',
    'jump_info_from_settings',
    '_FakeTransport',
    '_FakeChannel',
    '_FakeHostKeys',
    '_FakeClient',
    '_FakeSFTP',
    'make_connected_wrapper',
]

"""Contract tests for the one-hop SSH jump host.

These exercise the jump module's own behaviour - settings normalization, the
error mapping for authentication, bad host keys, missing transport and denied
forwarding, and the cleanup order - without claiming a real bastion round trip.
The end-to-end jump connect remains unproven (SFTP-014).
"""

from __future__ import annotations

import paramiko
import pytest

from hpc_gui.ssh import jump as jump_mod
from hpc_gui.ssh.host_keys import HostKeyChangedError
from hpc_gui.ssh.jump import (
    JumpAuthenticationError,
    JumpConnection,
    JumpConnectionError,
    JumpForwardingDeniedError,
    SSHJumpInfo,
    jump_info_from_settings,
)


class _FakeChannel:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


class _FakeTransport:
    def __init__(self, active=True, channel="default", error=None):
        self.active = active
        self._channel = channel
        self._error = error
        self.keepalive = None

    def is_active(self):
        return self.active

    def set_keepalive(self, value):
        self.keepalive = value

    def open_channel(self, kind, dest_addr=None, src_addr=None):
        if self._error is not None:
            raise self._error
        if self._channel == "default":
            return _FakeChannel()
        return self._channel


class _FakeClient:
    def __init__(self, *, connect_error=None, transport=None):
        self.connect_error = connect_error
        self.transport = transport
        self.closed = False
        self.connect_kwargs = None
        self.policy = None

    def load_system_host_keys(self):
        pass

    def load_host_keys(self, _path):
        pass

    def set_missing_host_key_policy(self, policy):
        self.policy = policy

    def connect(self, **kwargs):
        self.connect_kwargs = kwargs
        if self.connect_error is not None:
            raise self.connect_error

    def get_transport(self):
        return self.transport

    def close(self):
        self.closed = True


def _install(monkeypatch, client):
    monkeypatch.setattr(jump_mod.paramiko, "SSHClient", lambda: client)
    return client


INFO = SSHJumpInfo(enabled=True, host="bastion.example", port=2222, username="jumpuser")


@pytest.mark.unit
def test_settings_without_enable_or_host_are_unused():
    assert jump_info_from_settings(None) is None
    assert jump_info_from_settings({}) is None
    assert jump_info_from_settings({"enabled": False, "host": "b"}) is None
    assert jump_info_from_settings({"enabled": True, "host": ""}) is None


@pytest.mark.unit
def test_settings_become_typed_info():
    info = jump_info_from_settings(
        {"enabled": True, "host": "bastion", "port": 2200, "username": "u"}
    )
    assert isinstance(info, SSHJumpInfo)
    assert info.enabled is True
    assert info.host == "bastion"
    assert info.port == 2200
    assert info.username == "u"


@pytest.mark.unit
def test_authentication_failure_maps_and_closes(monkeypatch):
    client = _install(
        monkeypatch, _FakeClient(connect_error=paramiko.AuthenticationException("no"))
    )
    connection = JumpConnection(INFO, target_host="target", target_port=22)
    with pytest.raises(JumpAuthenticationError):
        connection.open()
    assert client.closed is True
    assert client.connect_kwargs["hostname"] == "bastion.example"
    assert client.connect_kwargs["port"] == 2222


@pytest.mark.unit
def test_bad_host_key_maps_to_host_key_changed(monkeypatch):
    _install(monkeypatch, _FakeClient(connect_error=paramiko.BadHostKeyException("h", b"k", b"e")))
    connection = JumpConnection(INFO, target_host="target", target_port=22)
    with pytest.raises(HostKeyChangedError):
        connection.open()


@pytest.mark.unit
def test_missing_active_transport_is_reported(monkeypatch):
    _install(monkeypatch, _FakeClient(transport=_FakeTransport(active=False)))
    connection = JumpConnection(INFO, target_host="target", target_port=22)
    with pytest.raises(JumpConnectionError):
        connection.open()


@pytest.mark.unit
def test_denied_forwarding_is_reported(monkeypatch):
    transport = _FakeTransport(error=paramiko.ChannelException(1, "denied"))
    _install(monkeypatch, _FakeClient(transport=transport))
    connection = JumpConnection(INFO, target_host="target", target_port=22)
    with pytest.raises(JumpForwardingDeniedError):
        connection.open()


@pytest.mark.unit
def test_none_channel_is_reported_as_denied(monkeypatch):
    _install(monkeypatch, _FakeClient(transport=_FakeTransport(channel=None)))
    connection = JumpConnection(INFO, target_host="target", target_port=22)
    with pytest.raises(JumpForwardingDeniedError):
        connection.open()


@pytest.mark.unit
def test_success_returns_channel_and_close_is_idempotent(monkeypatch):
    channel = _FakeChannel()
    transport = _FakeTransport(channel=channel)
    client = _install(monkeypatch, _FakeClient(transport=transport))
    connection = JumpConnection(
        INFO, target_host="target", target_port=22, known_hosts_path=""
    )

    returned = connection.open()

    assert returned is channel
    assert connection.channel is channel
    assert transport.keepalive is not None
    connection.close()
    connection.close()
    assert channel.closed is True
    assert client.closed is True

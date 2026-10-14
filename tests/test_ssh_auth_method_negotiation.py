import paramiko
import pytest
from paramiko.auth_strategy import AuthFailure

from hpc_gui.ssh.auth_strategy import _ConnectionAuthStrategy
from hpc_gui.ssh.client import SSHConnInfo


class _Transport:
    def __init__(self, allowed_methods):
        self.allowed_methods = allowed_methods
        self.calls = []

    def auth_none(self, _username):
        self.calls.append("none")
        raise paramiko.BadAuthenticationType("not allowed", self.allowed_methods)

    def auth_publickey(self, _username, _key):
        self.calls.append("publickey")
        raise paramiko.AuthenticationException("key rejected")

    def auth_password(self, _username, _password):
        self.calls.append("password")
        raise paramiko.AuthenticationException("password rejected")

    def auth_interactive(self, _username, _handler):
        self.calls.append("keyboard-interactive")
        raise AssertionError("server does not advertise keyboard-interactive")


def test_auth_strategy_skips_methods_not_offered_by_server():
    transport = _Transport(["publickey", "password"])
    info = SSHConnInfo(
        host="cluster",
        port=22,
        username="user",
        password="pw",
        keyboard_interactive_handler=lambda *_args: [],
        allow_agent=False,
        look_for_keys=False,
    )

    with pytest.raises(AuthFailure):
        _ConnectionAuthStrategy(info, pkey=object()).authenticate(transport)

    assert transport.calls == ["none", "publickey", "password"]


def test_partial_auth_uses_methods_returned_for_next_factor():
    class PartialTransport(_Transport):
        def auth_none(self, _username):
            self.calls.append("none")
            raise paramiko.BadAuthenticationType("not allowed", ["publickey"])

        def auth_publickey(self, _username, _key):
            self.calls.append("publickey")
            return ["password"]

        def auth_password(self, _username, _password):
            self.calls.append("password")
            return []

    transport = PartialTransport(["publickey"])
    info = SSHConnInfo(
        host="cluster",
        port=22,
        username="user",
        password="pw",
        keyboard_interactive_handler=lambda *_args: [],
        allow_agent=False,
        look_for_keys=False,
    )

    result = _ConnectionAuthStrategy(info, pkey=object()).authenticate(transport)

    assert result
    assert transport.calls == ["none", "publickey", "password"]

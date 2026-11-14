"""Isolated X11 forwarding protocol checks without a real X server.

The forwarder remains intentionally unconnected to the develop shell until
Windows/Ubuntu and authentication acceptance can be established.
"""

from __future__ import annotations

import struct

import pytest

from hpc_gui.ssh.x11_forward import (
    X11Forwarder,
    parse_display,
    rewrite_setup_auth,
)

pytestmark = pytest.mark.unit

COOKIE_NAME = b"MIT-MAGIC-COOKIE-1"


def _setup_packet(cookie: bytes, *, endian: str = "<") -> bytes:
    name = COOKIE_NAME
    def pad(length: int) -> bytes:
        return b"\0" * ((-length) % 4)
    order = b"l" if endian == "<" else b"B"
    header = order + b"\0" + struct.pack(endian + "HHHH", 11, 0, len(name), len(cookie)) + b"\0\0"
    return header + name + pad(len(name)) + cookie + pad(len(cookie))


@pytest.mark.parametrize("endian", ["<", ">"])
def test_auth_replaces_fake_cookie_with_local_cookie(endian):
    fake, real = b"A" * 16, b"B" * 16
    result = rewrite_setup_auth(_setup_packet(fake, endian=endian), fake, real)
    assert result == _setup_packet(real, endian=endian)
    assert fake not in result


def test_auth_refuses_invalid_cookie_and_invalid_endianness():
    fake = b"A" * 16
    assert rewrite_setup_auth(_setup_packet(b"WRONG-COOKIE-123"), fake, None) is None
    assert rewrite_setup_auth(b"z" + _setup_packet(fake)[1:], fake, None) is None


def test_missing_local_xauth_cookie_is_denied_by_default():
    fake = b"A" * 16
    assert rewrite_setup_auth(_setup_packet(fake), fake, None) is None


def test_explicit_trusted_loopback_mode_can_strip_auth_fields():
    fake = b"A" * 16
    result = rewrite_setup_auth(
        _setup_packet(fake), fake, None, allow_empty_auth=True
    )
    assert result is not None and result.startswith(b"l")
    assert struct.unpack("<HH", result[6:10]) == (0, 0)
    assert COOKIE_NAME not in result
    assert fake not in result


def test_auth_waits_for_complete_setup_header():
    fake = b"A" * 16
    packet = _setup_packet(fake)
    assert rewrite_setup_auth(packet[:10], fake, None) == b""
    assert rewrite_setup_auth(packet[:25], fake, None) == b""


def test_display_parsing_uses_local_x11_transport_when_available():
    linux = parse_display(":2.1", platform="linux")
    assert (linux.display, linux.screen, linux.unix_path) == (2, 1, "/tmp/.X11-unix/X2")
    windows = parse_display(":0", platform="win32")
    assert (windows.display, windows.host, windows.unix_path) == (0, "127.0.0.1", "")


def test_request_registers_handler_and_never_starts_processes():
    requested = []
    class Channel:
        def request_x11(self, **kwargs):
            requested.append(kwargs)

    relay = X11Forwarder(cookie_reader=lambda _display: b"B" * 16)
    try:
        relay.request(Channel())
        assert len(requested) == 1
        assert requested[0]["auth_protocol"] == "MIT-MAGIC-COOKIE-1"
        assert requested[0]["auth_cookie"] == relay.fake_cookie_hex
        assert requested[0]["handler"] == relay._on_x11_channel
    finally:
        relay.close()


@pytest.mark.parametrize(
    "unsafe_display",
    ["evil.example:0", "192.168.0.1:0", "10.0.0.8:1", ":59536", ":65536", "broken"],
)
def test_remote_display_and_invalid_port_are_rejected(unsafe_display):
    with pytest.raises(ValueError):
        parse_display(unsafe_display, platform="linux")


def test_direct_localdisplay_object_cannot_connect_to_remote_host():
    from hpc_gui.ssh.x11_forward import LocalDisplay

    remote = LocalDisplay(host="evil.example", display=0)
    with pytest.raises(ValueError, match="loopback"):
        remote.connect()


def test_forwarder_refuses_unsecured_x11_request_without_local_cookie():
    requested = []
    class Channel:
        def request_x11(self, **kwargs):
            requested.append(kwargs)

    relay = X11Forwarder(cookie_reader=lambda _: None)
    with pytest.raises(RuntimeError, match="cookie unavailable"):
        relay.request(Channel())
    assert requested == []
    relay.close()


def test_explicit_unauthenticated_mode_still_rejects_nonloopback_display():
    from hpc_gui.ssh.x11_forward import LocalDisplay

    relay = X11Forwarder(
        LocalDisplay(host="evil.example"),
        cookie_reader=lambda _: None,
        allow_unauthenticated_loopback=True,
    )
    class Channel:
        def request_x11(self, **kwargs):
            raise AssertionError("must not allow remote hosts")

    with pytest.raises(ValueError, match="Remote X11 DISPLAY"):
        relay.request(Channel())
    relay.close()


def test_relay_channel_count_is_bounded_and_closed_requests_rejected(monkeypatch):
    import hpc_gui.ssh.x11_forward as forwarder_module

    starts = []
    class FakeThread:
        def __init__(self, *, target, args, name, daemon):
            self.target = target
            self.args = args
        def start(self):
            starts.append(self)

    class Channel:
        def __init__(self):
            self.closed = False
        def close(self):
            self.closed = True

    relay = X11Forwarder(cookie_reader=lambda _: b"B" * 16)
    monkeypatch.setattr(forwarder_module.threading, "Thread", FakeThread)
    channels = [Channel() for _ in range(9)]
    for channel in channels:
        relay._on_x11_channel(channel, None)
    assert len(starts) == 8
    assert not any(channel.closed for channel in channels[:8])
    assert channels[8].closed is True
    relay.close()
    after_close = Channel()
    relay._on_x11_channel(after_close, None)
    assert after_close.closed is True
    assert len(starts) == 8

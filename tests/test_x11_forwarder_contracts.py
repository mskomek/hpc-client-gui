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


def test_auth_uses_empty_auth_fields_without_local_xauth_cookie():
    fake = b"A" * 16
    result = rewrite_setup_auth(_setup_packet(fake), fake, None)
    assert result is not None and result.startswith(b"l")
    # Auth protocol and cookie lengths are encoded in the setup header.
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

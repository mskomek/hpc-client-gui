"""Xauthority parsing and private-cookie persistence contracts."""

from __future__ import annotations

import os

import pytest

from hpc_gui.core.xauthority import (
    create_mit_cookie_file,
    create_untrusted_cookie,
    read_mit_cookie,
)
from hpc_gui.ssh import x11_forward
from hpc_gui.ssh.x11_forward import LocalDisplay

pytestmark = pytest.mark.unit


def test_cookie_round_trips_through_xauthority_file(tmp_path):
    authority = tmp_path / "server.xauth"
    cookie = create_mit_cookie_file(authority, 2)

    assert len(cookie) == 16
    assert read_mit_cookie(authority, 2) == cookie
    assert read_mit_cookie(authority, 1) is None
    if os.name == "posix":
        assert authority.stat().st_mode & 0o777 == 0o600


def test_malformed_authority_file_fails_closed(tmp_path):
    authority = tmp_path / "bad.xauth"
    authority.write_bytes(b"\xff\xff\x00\x02\x00")

    assert read_mit_cookie(authority, 0) is None


def test_windows_cookie_reader_uses_xauthority_file_when_xauth_is_absent(
    tmp_path, monkeypatch
):
    authority = tmp_path / "vcxsrv.xauth"
    cookie = create_mit_cookie_file(authority, 0)
    monkeypatch.setenv("XAUTHORITY", str(authority))
    monkeypatch.setattr(x11_forward, "find_xauth_executable", lambda: None)

    assert x11_forward.read_local_cookie(
        LocalDisplay(), runner=lambda *args, **kwargs: pytest.fail("xauth is unavailable")
    ) == cookie


def test_trusted_cookie_reader_uses_installed_vcxsrv_xauth(tmp_path, monkeypatch):
    authority = tmp_path / "vcxsrv.xauth"
    authority.touch()
    cookie = bytes.fromhex("1234567890abcdef1234567890abcdef")
    commands = []
    monkeypatch.setenv("XAUTHORITY", str(authority))
    monkeypatch.setattr(
        x11_forward, "find_xauth_executable", lambda: "VcXsrv/xauth.exe"
    )

    def runner(command, **_kwargs):
        commands.append(command)
        return type("Result", (), {
            "returncode": 0,
            "stdout": "DESKTOP/unix:0 MIT-MAGIC-COOKIE-1 " + cookie.hex() + "\n",
            "stderr": "",
        })()

    assert x11_forward.read_local_cookie(
        LocalDisplay(), runner=runner
    ) == cookie
    assert commands == [["VcXsrv/xauth.exe", "list", "localhost:0.0"]]


def test_untrusted_cookie_uses_private_authority_copy_and_cleans_it(tmp_path, monkeypatch):
    source = tmp_path / "source.xauth"
    trusted = create_mit_cookie_file(source, 0)
    monkeypatch.setattr("hpc_gui.core.xauthority.find_xauth_executable", lambda: "xauth")
    calls = []
    generated_cookie = bytes.fromhex("1234567890abcdef1234567890abcdef")

    def runner(command, **_kwargs):
        calls.append(command)
        if "generate" in command:
            return type("Result", (), {"returncode": 0, "stdout": "", "stderr": ""})()
        cookie = trusted if len([item for item in calls if "list" in item]) == 1 else generated_cookie
        return type("Result", (), {
            "returncode": 0,
            "stdout": "host/unix:0 MIT-MAGIC-COOKIE-1 " + cookie.hex() + "\n",
            "stderr": "",
        })()

    private, cookie = create_untrusted_cookie(source, ":0", runner=runner)
    assert private != source and private.exists()
    assert cookie == generated_cookie and cookie != trusted
    assert "list" in calls[0] and "generate" in calls[1]
    assert calls[0][0:2] == ["xauth", "-f"]
    private.unlink()


def test_untrusted_cookie_failure_does_not_create_fallback(tmp_path, monkeypatch):
    source = tmp_path / "source.xauth"
    create_mit_cookie_file(source, 0)
    monkeypatch.setattr("hpc_gui.core.xauthority.find_xauth_executable", lambda: "xauth")
    failure = type("Result", (), {"returncode": 1, "stdout": "", "stderr": ""})()
    with pytest.raises(RuntimeError, match="does not support untrusted"):
        create_untrusted_cookie(source, ":0", runner=lambda *_args, **_kwargs: failure)
    assert list(tmp_path.glob("hpc-x11-*.xauth")) == []

def test_default_forwarder_uses_untrusted_cookie_and_deletes_private_copy(tmp_path):
    authority = tmp_path / "private.xauth"
    authority.write_bytes(b"private authority")
    cookie = b"U" * 16
    calls = []

    def generate(source, name):
        calls.append((source, name))
        return authority, cookie

    forwarder = x11_forward.X11Forwarder(
        cookie_reader=lambda _display: pytest.fail("trusted cookie is forbidden by default"),
        untrusted_cookie_factory=generate,
    )
    try:
        assert forwarder._real_cookie == cookie
        assert len(calls) == 1
        assert calls[0][1] == forwarder.display.name
        assert not forwarder._allow_empty_auth
    finally:
        forwarder.close()
        forwarder.close()
    assert not authority.exists()


def test_explicit_trusted_forwarder_avoids_untrusted_cookie_generation():
    reader_called = []

    def cookie_reader(_display):
        reader_called.append(True)
        return b"T" * 16

    forwarder = x11_forward.X11Forwarder(
        trusted=True,
        cookie_reader=cookie_reader,
        untrusted_cookie_factory=lambda *_args: pytest.fail("must not generate untrusted"),
    )
    try:
        assert forwarder._real_cookie == b"T" * 16
        assert reader_called == [True]
    finally:
        forwarder.close()


def test_untrusted_cookie_failure_never_falls_back_to_trusted():
    with pytest.raises(RuntimeError, match="Untrusted X11 cookie unavailable"):
        x11_forward.X11Forwarder(
            cookie_reader=lambda _display: pytest.fail("must not use trusted fallback"),
            untrusted_cookie_factory=lambda *_args: (_ for _ in ()).throw(
                RuntimeError("SECURITY extension missing")
            ),
        )


def test_invalid_untrusted_cookie_removes_temporary_authority(tmp_path):
    authority = tmp_path / "generated.xauth"
    authority.write_text("sensitive", encoding="utf-8")
    with pytest.raises(RuntimeError, match="Untrusted X11 cookie unavailable"):
        x11_forward.X11Forwarder(
            untrusted_cookie_factory=lambda *_args: (authority, b"invalid"),
        )
    assert not authority.exists()


def test_unauthenticated_relay_cannot_be_enabled_in_untrusted_mode():
    with pytest.raises(ValueError, match="requires explicit trusted"):
        x11_forward.X11Forwarder(
            allow_unauthenticated_loopback=True,
            untrusted_cookie_factory=lambda *_args: pytest.fail("no generation expected"),
        )


def test_explicit_server_rejection_is_not_silent():
    class RejectedChannel:
        def request_x11(self, **_kwargs):
            return False

    forwarder = x11_forward.X11Forwarder(
        trusted=True, cookie_reader=lambda _display: b"C" * 16
    )
    try:
        with pytest.raises(RuntimeError, match="rejected X11 forwarding"):
            forwarder.request(RejectedChannel())
    finally:
        forwarder.close()

def test_untrusted_generation_that_reuses_trusted_cookie_fails_closed(
    tmp_path, monkeypatch
):
    source = tmp_path / "original.xauth"
    trusted = create_mit_cookie_file(source, 0)
    monkeypatch.setattr("hpc_gui.core.xauthority.find_xauth_executable", lambda: "xauth")

    def runner(command, **_kwargs):
        return type("Result", (), {
            "returncode": 0,
            "stdout": (
                "host/unix:0 MIT-MAGIC-COOKIE-1 " + trusted.hex() + "\n"
                if "list" in command else ""
            ),
            "stderr": "",
        })()

    with pytest.raises(RuntimeError, match="distinct untrusted"):
        create_untrusted_cookie(source, ":0", runner=runner)
    assert list(tmp_path.glob("hpc-x11-*.xauth")) == []


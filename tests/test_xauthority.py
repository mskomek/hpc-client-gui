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
    create_mit_cookie_file(source, 0)
    monkeypatch.setattr("hpc_gui.core.xauthority.find_xauth_executable", lambda: "xauth")
    calls = []

    def runner(command, **_kwargs):
        calls.append(command)
        if "generate" in command:
            return type("Result", (), {"returncode": 0, "stdout": "", "stderr": ""})()
        return type("Result", (), {
            "returncode": 0,
            "stdout": "host/unix:0 MIT-MAGIC-COOKIE-1 1234567890abcdef1234567890abcdef\n",
            "stderr": "",
        })()

    private, cookie = create_untrusted_cookie(source, ":0", runner=runner)
    assert private != source and private.exists()
    assert cookie == bytes.fromhex("1234567890abcdef1234567890abcdef")
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


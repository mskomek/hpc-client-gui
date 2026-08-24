from __future__ import annotations

from pathlib import Path
from unittest import mock

from hpc_gui.services import x11_runner, xserver_manager, x11_system_ssh
from hpc_gui.services.x11_system_ssh import build_x11_launch


def test_macos_xquartz_preflight_requires_xquartz_and_display(monkeypatch):
    monkeypatch.setattr(xserver_manager, "_is_macos", lambda: True)
    monkeypatch.setattr(Path, "exists", lambda self: True)
    monkeypatch.delenv("DISPLAY", raising=False)
    messages: list[str] = []

    assert not xserver_manager.ensure_xquartz_available(messages.append)
    assert "DISPLAY" in messages[-1]


def test_macos_x11_preflight_uses_system_ssh_and_never_plink():
    runner = x11_runner.X11Runner(log_cb=lambda _msg: None)
    with (
        mock.patch.object(x11_runner, "_is_macos", return_value=True),
        mock.patch.object(x11_runner, "_is_windows", return_value=False),
        mock.patch.object(runner, "_system_ssh_available", return_value=True),
        mock.patch.object(x11_runner, "ensure_x_server_running", return_value=True),
        mock.patch.object(x11_runner, "ensure_plink_available") as plink,
    ):
        assert runner.preflight(enabled=True)
    plink.assert_not_called()


def test_macos_system_ssh_sets_xauth_location(monkeypatch):
    monkeypatch.setattr(x11_system_ssh.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(Path, "exists", lambda self: True)
    with mock.patch("hpc_gui.services.x11_system_ssh.shutil.which", return_value="/usr/bin/ssh"):
        launch = build_x11_launch("host", 22, "user", "xclock")
    assert launch is not None
    assert "XAuthLocation=/opt/X11/bin/xauth" in launch.args


def test_macos_password_x11_is_explicitly_rejected():
    messages: list[str] = []
    runner = x11_runner.X11Runner(log_cb=messages.append)
    info = type("Info", (), {"x11_forwarding": True, "password": "secret", "key_path": ""})()
    with mock.patch.object(x11_runner, "_is_macos", return_value=True):
        assert runner.run_if_x11(info, "xclock") is True
    assert "password-only" in messages[0] or messages[0] == "[login.x11_macos_password_limit]"

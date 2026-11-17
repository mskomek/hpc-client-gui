"""Regression tests for starting the local X server used by X11 forwarding.

The 2026-11-12 regression was detected only after a manual run: discovery
found nothing, so the startup path was never exercised by the suite.  These
tests pin the behavior that makes ``DISPLAY`` appear on the remote side:
short-circuit a running server, start the discovered executable with TCP
listening, honor the concurrent-start cooldown, fail closed when the process
dies, and never prompt or download from the terminal path.
"""

from __future__ import annotations

import time

import pytest

from hpc_gui.services import process_registry, xserver_manager

pytestmark = pytest.mark.unit


class _Proc:
    def __init__(self, pid: int = 4242, exit_code: int | None = None) -> None:
        self.pid = pid
        self._exit_code = exit_code

    def poll(self):
        return self._exit_code


@pytest.fixture
def manager_paths(monkeypatch, tmp_path):
    monkeypatch.setattr(xserver_manager, "_is_windows", lambda: True)
    monkeypatch.setattr(xserver_manager, "_lock_path", lambda: tmp_path / "start.lock")
    monkeypatch.setattr(xserver_manager, "_pid_path", lambda: tmp_path / "pid.txt")
    monkeypatch.setattr(xserver_manager, "_stdout_log_path", lambda: tmp_path / "stdout.log")
    monkeypatch.setattr(xserver_manager, "_stderr_log_path", lambda: tmp_path / "stderr.log")
    monkeypatch.setattr(xserver_manager, "_auth_path_marker", lambda: tmp_path / "auth-path.txt")
    monkeypatch.setattr(xserver_manager, "_new_auth_path", lambda: tmp_path / "xserver.xauth")
    monkeypatch.setattr(xserver_manager, "_loopback_listener", lambda _display=0: True)
    monkeypatch.setattr(xserver_manager, "_LAST_START_TS", 0.0)
    monkeypatch.setattr(process_registry, "register", lambda *args, **kwargs: None)
    return tmp_path


def _exe(tmp_path):
    exe = tmp_path / "VcXsrv" / "vcxsrv.exe"
    exe.parent.mkdir(parents=True, exist_ok=True)
    exe.write_bytes(b"stub")
    return exe


def test_running_display_skips_lookup_and_start(monkeypatch, manager_paths):
    monkeypatch.setattr(xserver_manager, "_is_display_listening", lambda display=0: True)
    monkeypatch.setattr(xserver_manager, "_loopback_listener", lambda _display=0: True)
    monkeypatch.setattr(
        xserver_manager,
        "vcxsrv_executable_path",
        lambda: pytest.fail("a listening display must not trigger discovery"),
    )

    assert xserver_manager.ensure_x_server_running(log=lambda _m: None) is True


def test_starts_discovered_executable_with_tcp_listening(monkeypatch, manager_paths):
    exe = _exe(manager_paths)
    state = {"listening": False}
    captured = {}

    monkeypatch.setattr(xserver_manager, "vcxsrv_executable_path", lambda: exe)
    monkeypatch.setattr(xserver_manager, "_is_display_listening", lambda display=0: state["listening"])

    def fake_popen(args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        state["listening"] = True
        return _Proc()

    monkeypatch.setattr(xserver_manager.subprocess, "Popen", fake_popen)

    assert xserver_manager.ensure_x_server_running(log=lambda _m: None) is True
    args = captured["args"]
    assert args[0] == str(exe)
    assert args[1] == ":0"
    assert args[args.index("-listen") + 1] == "tcp"
    assert "-from" not in args
    assert args[args.index("-auth") + 1] == str(manager_paths / "xserver.xauth")
    assert (manager_paths / "xserver.xauth").is_file()
    assert (manager_paths / "auth-path.txt").read_text(encoding="utf-8") == str(
        manager_paths / "xserver.xauth"
    )
    assert "-multiwindow" in args
    assert "-ac" not in args
    assert captured["kwargs"]["cwd"] == str(exe.parent)
    assert (manager_paths / "pid.txt").read_text(encoding="utf-8") == "4242"


def test_concurrent_start_cooldown_waits_for_listener(monkeypatch, manager_paths):
    calls = {"count": 0}

    def listening(display=0):
        calls["count"] += 1
        return calls["count"] > 1

    monkeypatch.setattr(xserver_manager, "_LAST_START_TS", time.time())
    monkeypatch.setattr(xserver_manager, "_is_display_listening", listening)
    monkeypatch.setattr(xserver_manager, "_loopback_listener", lambda _display=0: True)
    monkeypatch.setattr(
        xserver_manager.subprocess,
        "Popen",
        lambda *a, **k: pytest.fail("cooldown must not spawn a second server"),
    )

    assert xserver_manager.ensure_x_server_running(log=lambda _m: None) is True


def test_process_that_exits_immediately_reports_failure(monkeypatch, manager_paths):
    exe = _exe(manager_paths)
    monkeypatch.setattr(xserver_manager, "vcxsrv_executable_path", lambda: exe)
    monkeypatch.setattr(xserver_manager, "_is_display_listening", lambda display=0: False)
    monkeypatch.setattr(xserver_manager.subprocess, "Popen", lambda *a, **k: _Proc(exit_code=1))

    assert xserver_manager.ensure_x_server_running(log=lambda _m: None) is False


def test_missing_server_never_prompts_or_downloads(monkeypatch, manager_paths):
    monkeypatch.setattr(xserver_manager, "_is_display_listening", lambda display=0: False)
    monkeypatch.setattr(xserver_manager, "vcxsrv_executable_path", lambda: None)
    monkeypatch.setattr(
        xserver_manager,
        "_prompt_install",
        lambda *args, **kwargs: pytest.fail("the terminal path must not prompt"),
    )

    assert (
        xserver_manager.ensure_x_server_running(
            log=lambda _m: None, parent=object(), allow_download=False
        )
        is False
    )


def test_existing_non_loopback_server_is_refused(monkeypatch, manager_paths):
    monkeypatch.setattr(xserver_manager, "_is_display_listening", lambda display=0: True)
    monkeypatch.setattr(xserver_manager, "_loopback_listener", lambda _display=0: False)
    monkeypatch.setattr(
        xserver_manager,
        "vcxsrv_executable_path",
        lambda: pytest.fail("must refuse an unsafe listener, not start another server"),
    )
    messages = []

    assert xserver_manager.ensure_x_server_running(log=messages.append) is False
    assert any("not restricted to loopback" in message for message in messages)


def test_owned_wildcard_listener_requires_and_accepts_firewall_proof(monkeypatch, manager_paths):
    monkeypatch.setattr(xserver_manager, "_is_display_listening", lambda display=0: True)
    monkeypatch.setattr(xserver_manager, "_loopback_listener", lambda _display=0: False)
    monkeypatch.setattr(xserver_manager, "_app_firewall_listener", lambda _display=0: True)
    monkeypatch.setattr(
        xserver_manager,
        "vcxsrv_executable_path",
        lambda: pytest.fail("verified app-owned server should be reused"),
    )

    assert xserver_manager.ensure_x_server_running(log=lambda _message: None) is True

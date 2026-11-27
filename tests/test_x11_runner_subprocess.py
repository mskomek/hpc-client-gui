"""Real local subprocess lifecycle and explicit consent for legacy X11 helpers."""
from __future__ import annotations

import sys
import time
from types import SimpleNamespace

import pytest

from hpc_gui.services import process_registry, putty_manager, x11_runner, xserver_manager
from hpc_gui.services.x11_system_ssh import X11Launch


def _until(predicate):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(.01)
    assert predicate(), "X11 subprocess lifecycle did not finish"


@pytest.fixture
def local_runner(monkeypatch):
    messages, registered, unregistered = [], [], []
    monkeypatch.setattr(x11_runner, "_is_macos", lambda: False)
    monkeypatch.setattr(x11_runner, "ensure_x_server_running", lambda *a, **k: True)
    monkeypatch.setattr(process_registry, "register", lambda pid, **kw: registered.append((pid, kw)))
    monkeypatch.setattr(process_registry, "unregister", unregistered.append)
    runner = x11_runner.X11Runner(log_cb=messages.append)
    info = SimpleNamespace(x11_forwarding=True, host="example.invalid", port=22,
                           username="test", password=None, key_path=None)
    try:
        yield runner, info, messages, registered, unregistered
    finally:
        runner.shutdown(close_x11_procs=True, close_vcxsrv=False)


@pytest.mark.integration
@pytest.mark.resource
def test_real_x11_subprocess_drains_both_streams_and_reaps(monkeypatch, local_runner):
    runner, info, messages, registered, unregistered = local_runner
    monkeypatch.setattr(x11_runner, "build_x11_launch", lambda **kw: X11Launch(
        sys.executable, ["-u", "-c", "import os,sys; print('OUT:'+os.environ['DISPLAY']); "
                         "print('ERR:unicode', file=sys.stderr); sys.exit(7)"], "ssh"))
    monkeypatch.setenv("DISPLAY", "test-display")
    assert runner.run_if_x11(info, "xclock")
    _until(lambda: bool(unregistered))
    _until(lambda: any("7" in m for m in messages))
    assert any("OUT:test-display" in m for m in messages)
    assert any("ERR:unicode" in m for m in messages)
    assert len(registered) == 1
    assert registered[0][1] == {"kind": "x11_ssh"}
    assert unregistered == [registered[0][0]]
    assert not runner._bg_procs


@pytest.mark.integration
@pytest.mark.resource
def test_x11_shutdown_terminates_only_owned_process(monkeypatch, local_runner):
    runner, info, messages, registered, unregistered = local_runner
    monkeypatch.setattr(x11_runner, "build_x11_launch", lambda **kw: X11Launch(
        sys.executable, ["-u", "-c", "import time; print('READY'); time.sleep(60)"], "ssh"))
    assert runner.run_if_x11(info, "xclock")
    _until(lambda: any("READY" == m for m in messages))
    proc = runner._bg_procs[0]
    runner.shutdown(close_x11_procs=False, close_vcxsrv=False)
    assert proc.poll() is None
    runner.shutdown(close_x11_procs=True, close_vcxsrv=False)
    _until(lambda: bool(unregistered))
    assert proc.poll() is not None
    assert unregistered == [registered[0][0]]
    assert not runner._bg_procs


@pytest.mark.unit
def test_x11_launch_failure_does_not_register_nonexistent_process(monkeypatch, local_runner):
    runner, info, messages, registered, unregistered = local_runner
    monkeypatch.setattr(x11_runner, "build_x11_launch", lambda **kw: X11Launch(
        "missing-test-executable", [], "ssh"))
    assert runner.run_if_x11(info, "xclock")
    assert messages
    assert not registered and not unregistered and not runner._bg_procs


@pytest.mark.unit
def test_putty_requires_explicit_consent_before_official_page(monkeypatch, tmp_path):
    monkeypatch.setattr(putty_manager.platform, "system", lambda: "Windows")
    monkeypatch.setattr(putty_manager.shutil, "which", lambda name: None)
    monkeypatch.setattr(putty_manager, "plink_path", lambda: tmp_path / "missing.exe")
    opened = []
    monkeypatch.setattr(putty_manager.webbrowser, "open", opened.append)
    parent = object()
    assert not putty_manager.ensure_plink_available(parent=parent)
    assert not putty_manager.ensure_plink_available(parent=parent, confirm=lambda *a: False)
    assert not opened
    assert not putty_manager.ensure_plink_available(parent=parent, confirm=lambda *a: True)
    assert opened == ["https://www.chiark.greenend.org.uk/~sgtatham/putty/latest.html"]


@pytest.mark.unit
def test_xserver_requires_explicit_consent_and_never_downloads(monkeypatch):
    monkeypatch.setattr(xserver_manager, "_is_windows", lambda: True)
    monkeypatch.setattr(xserver_manager, "_is_macos", lambda: False)
    monkeypatch.setattr(xserver_manager, "_is_display_listening", lambda *a: False)
    monkeypatch.setattr(xserver_manager, "vcxsrv_executable_path", lambda: None)
    monkeypatch.setattr(xserver_manager, "_LAST_START_TS", 0.0)
    opened = []
    monkeypatch.setattr(xserver_manager.webbrowser, "open", opened.append)
    parent = object()
    assert not xserver_manager.ensure_x_server_running(parent=parent)
    assert not xserver_manager.ensure_x_server_running(parent=parent, confirm=lambda *a: False)
    assert not opened
    assert not xserver_manager.ensure_x_server_running(parent=parent, confirm=lambda *a: True)
    assert opened == ["https://sourceforge.net/projects/vcxsrv/files/vcxsrv/"]

"""Startup checks are real local probes and safe process-record cleanup."""
from __future__ import annotations

import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

import pytest

from hpc_gui.services import process_registry as registry
from hpc_gui.startup_checks import check_startup_helpers


@pytest.mark.unit
def test_startup_checks_backend_apis_without_killing_or_connecting(monkeypatch):
    from hpc_gui.ssh.client import SSHClientWrapper

    calls = []
    monkeypatch.setattr(registry, "cleanup_orphans", lambda **kwargs: calls.append(kwargs))
    monkeypatch.setattr(SSHClientWrapper, "connect", lambda *a, **k: pytest.fail("network called"))
    assert check_startup_helpers() == {"SSH backend": True, "SFTP backend": True}
    assert calls == [{"aggressive": False}]


@pytest.mark.unit
def test_unknown_or_live_processes_are_preserved(monkeypatch, tmp_path):
    monkeypatch.setattr(registry, "_registry_path", lambda: tmp_path / "processes.json")
    monkeypatch.setattr(registry, "_pid_exists", lambda pid: {11: False, 12: True, 13: None}[pid])
    monkeypatch.setattr(registry, "_kill_tree_windows", lambda *a: pytest.fail("process kill"))
    for pid in (11, 12, 13):
        registry.register(pid, kind="x11_test")
    registry.cleanup_orphans(aggressive=False)
    assert set(registry._read_all()) == {"12", "13"}


@pytest.mark.unit
def test_concurrent_registry_updates_are_not_lost(monkeypatch, tmp_path):
    monkeypatch.setattr(registry, "_registry_path", lambda: tmp_path / "processes.json")
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda pid: registry.register(pid, kind="test"), range(100, 124)))
    assert set(registry._read_all()) == {str(pid) for pid in range(100, 124)}
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(registry.unregister, range(100, 112)))
    assert set(registry._read_all()) == {str(pid) for pid in range(112, 124)}


@pytest.mark.unit
def test_process_probe_recognizes_live_current_process():
    assert registry._pid_exists(os.getpid()) is True


@pytest.mark.unit
def test_real_child_record_is_only_removed_after_exit(monkeypatch, tmp_path):
    monkeypatch.setattr(registry, "_registry_path", lambda: tmp_path / "processes.json")
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    try:
        registry.register(child.pid, kind="x11_test")
        registry.cleanup_orphans()
        assert str(child.pid) in registry._read_all()
    finally:
        child.terminate()
        child.wait(timeout=10)
    # PID reuse is possible, so only remove a record after confirmed absence.
    if registry._pid_exists(child.pid) is False:
        registry.cleanup_orphans()
        assert str(child.pid) not in registry._read_all()

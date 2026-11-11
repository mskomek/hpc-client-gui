"""VcXsrv discovery must see installer default locations.

The 2026-11-06 acceptance installed VcXsrv per-user under
``%LOCALAPPDATA%\\Programs\\VcXsrv``.  Discovery only looked at ``PATH`` and
``Program Files``, so the terminal silently opened without X11 forwarding and
remote ``$DISPLAY`` stayed empty.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hpc_gui.services import xserver_manager

pytestmark = pytest.mark.unit


@pytest.fixture
def clean_env(monkeypatch, tmp_path):
    """Isolate discovery from this machine's real installs."""

    for name in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA", "APPDATA"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(xserver_manager.shutil, "which", lambda _name: None)
    monkeypatch.setattr(xserver_manager, "third_party_dir", lambda: tmp_path / "third_party")
    return tmp_path


def _install(root: Path) -> Path:
    exe = root / "vcxsrv.exe"
    exe.parent.mkdir(parents=True, exist_ok=True)
    exe.write_bytes(b"stub")
    return exe


def test_per_user_installer_location_is_discovered(clean_env, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(clean_env / "local"))
    exe = _install(clean_env / "local" / "Programs" / "VcXsrv")

    assert xserver_manager.vcxsrv_executable_path() == exe


def test_system_install_wins_over_per_user_copy(clean_env, monkeypatch):
    monkeypatch.setenv("ProgramFiles", str(clean_env / "pf"))
    monkeypatch.setenv("LOCALAPPDATA", str(clean_env / "local"))
    system = _install(clean_env / "pf" / "VcXsrv")
    _install(clean_env / "local" / "Programs" / "VcXsrv")

    assert xserver_manager.vcxsrv_executable_path() == system


@pytest.mark.parametrize("subdir", ["runtime", ""])
def test_app_managed_install_from_older_releases_is_discovered(clean_env, subdir):
    managed = clean_env / "third_party" / "vcxsrv"
    exe = _install(managed / subdir if subdir else managed)

    assert xserver_manager.vcxsrv_executable_path() == exe


def test_missing_server_returns_none(clean_env):
    assert xserver_manager.vcxsrv_executable_path() is None

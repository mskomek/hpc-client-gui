"""VcXsrv discovery supports Windows per-user and system installers."""

from pathlib import Path

import pytest

from hpc_gui.services import xserver_manager

pytestmark = pytest.mark.unit


@pytest.fixture
def isolated_discovery(monkeypatch, tmp_path):
    for name in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA", "APPDATA"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(xserver_manager.shutil, "which", lambda _name: None)
    return tmp_path


def _install(root: Path, name: str = "vcxsrv.exe") -> Path:
    exe = root / name
    exe.parent.mkdir(parents=True, exist_ok=True)
    exe.write_bytes(b"test stub")
    return exe


@pytest.mark.parametrize("var", ["LOCALAPPDATA", "APPDATA"])
@pytest.mark.parametrize("binary", ["vcxsrv.exe", "XWin.exe"])
def test_per_user_vcxsrv_paths(isolated_discovery, monkeypatch, var, binary):
    root = isolated_discovery / var.lower()
    monkeypatch.setenv(var, str(root))
    exe = _install(root / "Programs" / "VcXsrv", binary)
    assert xserver_manager.vcxsrv_executable_path() == exe


def test_system_install_precedes_per_user(isolated_discovery, monkeypatch):
    system_root = isolated_discovery / "system"
    user_root = isolated_discovery / "local"
    monkeypatch.setenv("ProgramFiles", str(system_root))
    monkeypatch.setenv("LOCALAPPDATA", str(user_root))
    expected = _install(system_root / "VcXsrv")
    _install(user_root / "Programs" / "VcXsrv")
    assert xserver_manager.vcxsrv_executable_path() == expected


def test_missing_executable_returns_none(isolated_discovery):
    assert xserver_manager.vcxsrv_executable_path() is None

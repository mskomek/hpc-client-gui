import os
import plistlib
import stat
import subprocess
from pathlib import Path

import pytest

from hpc_gui.services.updater_helper import (
    APP_ID,
    HelperConfig,
    ProgressGuard,
    flatpak_command,
    install_appimage,
    install_deb,
    install_flatpak,
    install_macos,
)


class Process:
    def __init__(self, code=None):
        self.code = code

    def poll(self):
        return self.code


def config(tmp_path: Path, strategy: str, package: Path, target: Path) -> HelperConfig:
    return HelperConfig(strategy, package, target, 1, "2.0.0", "x86_64")


def test_progress_guard_never_decreases():
    values = []
    guard = ProgressGuard(lambda value, _status: values.append(value))
    guard(40, "copy")
    guard(20, "copy")
    guard(100, "done")
    assert values == [40, 40, 100]


def test_appimage_copies_bytes_preserves_executable_and_cleans_backup(monkeypatch, tmp_path: Path):
    target = tmp_path / "client.AppImage"
    package = tmp_path / "new.AppImage"
    target.write_bytes(b"old")
    package.write_bytes(b"new" * 1024 * 1024)
    os.chmod(target, 0o755)
    values = []

    monkeypatch.setattr("hpc_gui.services.updater_helper._healthy", lambda _process: True)
    install_appimage(config(tmp_path, "linux-appimage", package, target), lambda value, _status: values.append(value), lambda *_args, **_kwargs: Process())

    assert target.read_bytes() == package.read_bytes()
    if os.name != "nt":
        assert target.stat().st_mode & stat.S_IXUSR
    assert not target.with_name(target.name + ".backup").exists()
    assert values == sorted(values) and values[-1] == 100


def test_appimage_rolls_back_when_new_process_fails(monkeypatch, tmp_path: Path):
    target = tmp_path / "client.AppImage"
    package = tmp_path / "new.AppImage"
    target.write_bytes(b"old")
    package.write_bytes(b"new")
    launches = []

    def popen(command, **_kwargs):
        launches.append(command)
        return Process(1 if len(launches) == 1 else None)

    monkeypatch.setattr("hpc_gui.services.updater_helper._healthy", lambda process: process.code != 1)
    with pytest.raises(RuntimeError, match="exited"):
        install_appimage(config(tmp_path, "linux-appimage", package, target), lambda *_: None, popen)
    assert target.read_bytes() == b"old"
    assert len(launches) == 2


def test_deb_delegates_to_pkexec_apt_verifies_and_restarts(tmp_path: Path):
    package = tmp_path / "update.deb"
    target = tmp_path / "hpc-client-gui"
    package.write_bytes(b"deb")
    target.write_bytes(b"exe")
    commands = []

    def runner(command, **_kwargs):
        commands.append(command)
        stdout = {
            "pkcon": "install-local\n",
            "dpkg-query": "2.0.0",
        }.get(command[0], "")
        return subprocess.CompletedProcess(command, 0, stdout, "")

    launches = []
    install_deb(config(tmp_path, "linux-deb", package, target), lambda *_: None, runner, lambda command, **_kwargs: launches.append(command))
    assert commands[0] == ["pkcon", "get-actions"]
    assert commands[1] == ["pkcon", "install-local", str(package.resolve())]
    assert commands[2][0] == "dpkg-query"
    assert commands[3] == ["dpkg", "--compare-versions", "2.0.0", "ge", "2.0.0"]
    assert launches == [[str(target)]]


def test_deb_stops_when_packagekit_local_install_is_unavailable(tmp_path: Path):
    package = tmp_path / "update.deb"
    package.write_bytes(b"deb")
    commands = []

    def runner(command, **_kwargs):
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, "repair\n", "")

    with pytest.raises(RuntimeError, match="does not support local package installation"):
        install_deb(config(tmp_path, "linux-deb", package, tmp_path / "app"), lambda *_: None, runner)
    assert commands == [["pkcon", "get-actions"]]


def test_deb_authentication_failure_is_not_repaired_manually(tmp_path: Path):
    package = tmp_path / "update.deb"
    package.write_bytes(b"deb")
    result = subprocess.CompletedProcess([], 126, "", "authorization cancelled")
    launches = []
    def runner(command, **_kwargs):
        if command == ["pkcon", "get-actions"]:
            return subprocess.CompletedProcess(command, 0, "install-local\n", "")
        return result

    with pytest.raises(RuntimeError, match="authorization cancelled"):
        install_deb(config(tmp_path, "linux-deb", package, tmp_path / "app"), lambda *_: None, runner, lambda command, **_kwargs: launches.append(command))
    assert launches == [[str(tmp_path / "app")]]


def test_flatpak_uses_flatpak_for_bundle_and_restart(monkeypatch, tmp_path: Path):
    package = tmp_path / "update.flatpak"
    package.write_bytes(b"bundle")
    cfg = config(tmp_path, "linux-flatpak", package, tmp_path / "ignored")
    monkeypatch.delenv("FLATPAK_ID", raising=False)
    commands = []

    def runner(command, **_kwargs):
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, "ok", "")

    launches = []
    install_flatpak(cfg, lambda *_: None, runner, lambda command, **_kwargs: launches.append(command))
    assert commands[0][:5] == ["flatpak", "install", "--user", "--reinstall", "-y"]
    assert launches == [["flatpak", "run", APP_ID]]
    assert flatpak_command(cfg, False)[0] == "flatpak"


def test_flatpak_system_scope_remote_update_uses_manager_only(tmp_path: Path):
    cfg = HelperConfig("linux-flatpak", tmp_path / "missing.flatpak", tmp_path / "ignored", 1, "2.0", "x86_64", "system")
    assert flatpak_command(cfg, False) == [
        "flatpak", "update", "--system", "-y", APP_ID
    ]


def test_macos_validates_replaces_rolls_back_and_detaches(monkeypatch, tmp_path: Path):
    target = tmp_path / "HPC Client GUI.app"
    source = tmp_path / "mounted" / "HPC Client GUI.app"
    package = tmp_path / "update.dmg"
    package.write_bytes(b"dmg")
    (target / "Contents").mkdir(parents=True)
    (target / "Contents" / "old").write_bytes(b"old")
    executable = source / "Contents" / "MacOS" / "HPC Client GUI"
    executable.parent.mkdir(parents=True)
    executable.write_bytes(b"new")
    (source / "Contents" / "Info.plist").write_bytes(plistlib.dumps({"CFBundleIdentifier": APP_ID}))
    attach = plistlib.dumps({"system-entities": [{"mount-point": str(source.parent)}]}).decode()
    commands = []

    def runner(command, **_kwargs):
        commands.append(command)
        stdout = attach if command[:2] == ["hdiutil", "attach"] else ("x86_64" if command[0] == "lipo" else "")
        return subprocess.CompletedProcess(command, 0, stdout, "")

    monkeypatch.setattr("hpc_gui.services.updater_helper._healthy", lambda _process: True)
    install_macos(config(tmp_path, "macos-bundle", package, target), lambda *_: None, runner, lambda *_args, **_kwargs: Process())
    assert (target / "Contents" / "MacOS" / "HPC Client GUI").read_bytes() == b"new"
    assert commands[-1][:2] == ["hdiutil", "detach"]
    assert not target.with_name(target.name + ".backup").exists()


def test_macos_rolls_back_after_failed_launch(monkeypatch, tmp_path: Path):
    target = tmp_path / "HPC Client GUI.app"
    source = tmp_path / "mounted" / "HPC Client GUI.app"
    package = tmp_path / "update.dmg"
    package.write_bytes(b"dmg")
    (target / "Contents").mkdir(parents=True)
    (target / "Contents" / "old").write_bytes(b"old")
    executable = source / "Contents" / "MacOS" / "HPC Client GUI"
    executable.parent.mkdir(parents=True)
    executable.write_bytes(b"new")
    (source / "Contents" / "Info.plist").write_bytes(plistlib.dumps({"CFBundleIdentifier": APP_ID}))
    attach = plistlib.dumps({"system-entities": [{"mount-point": str(source.parent)}]}).decode()

    def runner(command, **_kwargs):
        stdout = attach if command[:2] == ["hdiutil", "attach"] else ("x86_64" if command[0] == "lipo" else "")
        return subprocess.CompletedProcess(command, 0, stdout, "")

    launches = []
    monkeypatch.setattr("hpc_gui.services.updater_helper._healthy", lambda process: process.code != 1)
    with pytest.raises(RuntimeError, match="failed to launch"):
        install_macos(config(tmp_path, "macos-bundle", package, target), lambda *_: None, runner, lambda *_args, **_kwargs: launches.append(True) or Process(1 if len(launches) == 1 else None))
    assert (target / "Contents" / "old").read_bytes() == b"old"
    assert len(launches) == 2

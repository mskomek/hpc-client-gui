"""Independent updater process for self-owned and package-managed installs."""

from __future__ import annotations

import json
import os
import plistlib
import shutil
import stat
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from hpc_gui.services.deb_installer import build_packagekit_command, probe_packagekit
from typing import Callable

APP_ID = "io.github.mskomek.HpcClientGui"
Progress = Callable[[int | None, str], None]
Runner = Callable[..., subprocess.CompletedProcess]


@dataclass(frozen=True)
class HelperConfig:
    strategy: str
    package: Path
    target: Path
    current_pid: int
    version: str
    architecture: str = ""
    flatpak_scope: str = "user"
    source_bundle: Path | None = None
    mount_point: Path | None = None

    @classmethod
    def load(cls, path: Path) -> "HelperConfig":
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            strategy=str(data["strategy"]),
            package=Path(data["package"]).resolve(),
            target=Path(data["target"]).resolve(),
            current_pid=int(data["current_pid"]),
            version=str(data["version"]),
            architecture=str(data.get("architecture") or ""),
            flatpak_scope=str(data.get("flatpak_scope") or "user"),
            source_bundle=Path(data["source_bundle"]).resolve() if data.get("source_bundle") else None,
            mount_point=Path(data["mount_point"]).resolve() if data.get("mount_point") else None,
        )


class ProgressGuard:
    def __init__(self, callback: Progress):
        self.callback = callback
        self.last = 0

    def __call__(self, value: int | None, status: str) -> None:
        if value is None:
            self.callback(None, status)
            return
        self.last = max(self.last, min(100, value))
        self.callback(self.last, status)


def _log(path: Path, message: str) -> None:
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with path.open("a", encoding="utf-8") as output:
        output.write(f"{stamp} {message}\n")


def wait_for_process(pid: int, timeout: float = 60.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except (OSError, ProcessLookupError):
            return
        time.sleep(0.1)
    raise RuntimeError("Application did not close before the update timeout.")


def _copy_file(source: Path, target: Path, start: int, end: int, progress: Progress) -> None:
    total = max(1, source.stat().st_size)
    done = 0
    target.parent.mkdir(parents=True, exist_ok=True)
    with source.open("rb") as src, target.open("xb") as dst:
        while chunk := src.read(1024 * 1024):
            dst.write(chunk)
            done += len(chunk)
            progress(start + int((end - start) * done / total), f"Copying: {target.name}")
        dst.flush()
        os.fsync(dst.fileno())


def _healthy(process: subprocess.Popen, seconds: float = 5.0) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        code = process.poll()
        if code is not None:
            return code == 0
        time.sleep(0.1)
    return True


def install_appimage(config: HelperConfig, progress: Progress, popen=subprocess.Popen) -> None:
    target = config.target
    package = config.package
    if target.is_symlink() or not target.is_file() or not os.access(target.parent, os.W_OK):
        raise RuntimeError("The AppImage target is not a writable regular file.")
    staged = target.with_name(target.name + ".new")
    backup = target.with_name(target.name + ".backup")
    staged.unlink(missing_ok=True)
    progress(15, "Validating AppImage target...")
    try:
        _copy_file(package, staged, 25, 90, progress)
        os.chmod(staged, target.stat().st_mode | stat.S_IXUSR)
        backup.unlink(missing_ok=True)
        target.replace(backup)
        staged.replace(target)
        progress(95, "Starting application...")
        process = popen([str(target)], cwd=str(target.parent), close_fds=True)
        if not _healthy(process):
            raise RuntimeError("Updated AppImage exited during startup.")
        backup.unlink(missing_ok=True)
        progress(100, "Update complete.")
    except Exception:
        progress(95, "Restoring previous version...")
        staged.unlink(missing_ok=True)
        if backup.exists():
            target.unlink(missing_ok=True)
            backup.replace(target)
            try:
                popen([str(target)], cwd=str(target.parent), close_fds=True)
            except OSError:
                pass
        raise


def _run_checked(command: list[str], runner: Runner) -> subprocess.CompletedProcess:
    result = runner(command, capture_output=True, text=True, check=False)
    if result.returncode:
        detail = (result.stderr or result.stdout or "command failed").strip()[-1000:]
        raise RuntimeError(detail)
    return result


def install_deb(config: HelperConfig, progress: Progress, runner=subprocess.run, popen=subprocess.Popen) -> None:
    if config.package.suffix.lower() != ".deb" or not config.package.is_file():
        raise RuntimeError("Verified DEB package is missing.")
    try:
        capability = probe_packagekit(runner)
        if not capability.local_install:
            raise RuntimeError(capability.reason)
        progress(None, "Requesting administrator permission...")
        _run_checked(build_packagekit_command(config.package), runner)
        progress(None, "Verifying installed version...")
        result = _run_checked(
            ["dpkg-query", "-W", "-f=${Version}", "hpc-client-gui"], runner
        )
        _run_checked(
            ["dpkg", "--compare-versions", result.stdout.strip(), "ge", config.version], runner
        )
    except Exception:
        try:
            popen([str(config.target)], close_fds=True)
        except OSError:
            pass
        raise
    progress(100, "Starting application...")
    popen([str(config.target)], close_fds=True)


def flatpak_command(config: HelperConfig, host_spawn: bool) -> list[str]:
    prefix = ["flatpak-spawn", "--host"] if host_spawn else []
    scope = "--user" if config.flatpak_scope == "user" else "--system"
    if config.package.is_file():
        return prefix + [
            "flatpak", "install", scope, "--reinstall", "-y", str(config.package)
        ]
    return prefix + ["flatpak", "update", scope, "-y", APP_ID]


def install_flatpak(config: HelperConfig, progress: Progress, runner=subprocess.run, popen=subprocess.Popen) -> None:
    host_spawn = bool(os.environ.get("FLATPAK_ID"))
    if host_spawn and not shutil.which("flatpak-spawn"):
        raise RuntimeError("Flatpak host update handoff is unavailable.")
    prefix = ["flatpak-spawn", "--host"] if host_spawn else []
    try:
        progress(None, "Updating application with Flatpak...")
        _run_checked(flatpak_command(config, host_spawn), runner)
        progress(None, "Verifying installation...")
        _run_checked(prefix + ["flatpak", "info", APP_ID], runner)
    except Exception:
        try:
            popen(prefix + ["flatpak", "run", APP_ID], close_fds=True)
        except OSError:
            pass
        raise
    progress(100, "Starting application...")
    popen(prefix + ["flatpak", "run", APP_ID], close_fds=True)


def _copy_tree(source: Path, target: Path, progress: Progress) -> None:
    files = [path for path in source.rglob("*") if path.is_file() and not path.is_symlink()]
    total = max(1, sum(path.stat().st_size for path in files))
    done = 0
    target.mkdir(parents=True)
    for path in source.rglob("*"):
        relative = path.relative_to(source)
        target_path = target / relative
        if path.is_symlink():
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.symlink_to(os.readlink(path), target_is_directory=path.resolve().is_dir())
        elif path.is_dir():
            target_path.mkdir(parents=True, exist_ok=True)
    for source_file in files:
        relative = source_file.relative_to(source)
        target_file = target / relative
        target_file.parent.mkdir(parents=True, exist_ok=True)
        with source_file.open("rb") as src, target_file.open("xb") as dst:
            while chunk := src.read(1024 * 1024):
                dst.write(chunk)
                done += len(chunk)
                progress(35 + int(55 * done / total), f"Copying: {relative.as_posix()}")
        shutil.copystat(source_file, target_file, follow_symlinks=False)
    for directory in sorted((p for p in source.rglob("*") if p.is_dir()), reverse=True):
        shutil.copystat(directory, target / directory.relative_to(source), follow_symlinks=False)
    shutil.copystat(source, target, follow_symlinks=False)


def install_macos(config: HelperConfig, progress: Progress, runner=subprocess.run, popen=subprocess.Popen) -> None:
    if config.target.suffix != ".app" or not os.access(config.target.parent, os.W_OK):
        raise RuntimeError("The macOS application bundle is not writable.")
    progress(15, "Mounting update image...")
    mount = config.mount_point
    source = config.source_bundle
    if source is None or mount is None:
        attached = _run_checked(["hdiutil", "attach", "-nobrowse", "-plist", str(config.package)], runner)
        mount_points = [
            item.get("mount-point")
            for item in plistlib.loads(attached.stdout.encode()).get("system-entities", [])
            if item.get("mount-point")
        ]
        if not mount_points:
            raise RuntimeError("The update image did not mount.")
        mount = Path(mount_points[-1])
        source = mount / "HPC Client GUI.app"
    backup = config.target.with_name(config.target.name + ".backup")
    staged = config.target.with_name(config.target.name + ".new")
    try:
        info = plistlib.loads((source / "Contents" / "Info.plist").read_bytes())
        if info.get("CFBundleIdentifier") != APP_ID:
            raise RuntimeError("The update bundle identity is invalid.")
        _run_checked(["codesign", "--verify", "--deep", "--strict", str(source)], runner)
        _run_checked(["spctl", "--assess", "--type", "execute", str(source)], runner)
        arch = _run_checked(["lipo", "-archs", str(source / "Contents" / "MacOS" / "HPC Client GUI")], runner).stdout.split()
        if config.architecture not in arch:
            raise RuntimeError("The update bundle architecture is invalid.")
        shutil.rmtree(staged, ignore_errors=True)
        _copy_tree(source, staged, progress)
        shutil.rmtree(backup, ignore_errors=True)
        config.target.replace(backup)
        staged.replace(config.target)
        progress(95, "Starting application...")
        process = popen(["open", "-n", "-W", str(config.target)], close_fds=True)
        if not _healthy(process):
            raise RuntimeError("Updated application failed to launch.")
        shutil.rmtree(backup)
        progress(100, "Update complete.")
    except Exception:
        progress(95, "Restoring previous version...")
        shutil.rmtree(staged, ignore_errors=True)
        if backup.exists():
            shutil.rmtree(config.target, ignore_errors=True)
            backup.replace(config.target)
            try:
                popen(["open", "-n", str(config.target)], close_fds=True)
            except OSError:
                pass
        raise
    finally:
        runner(["hdiutil", "detach", str(mount)], capture_output=True, text=True, check=False)


def perform_update(config: HelperConfig, progress: Progress, runner=subprocess.run, popen=subprocess.Popen) -> None:
    log_path = config.package.parent / "update-install.log"
    _log(log_path, f"Updater started; strategy: {config.strategy}")
    guarded_progress = ProgressGuard(progress)
    last_phase = ""

    def guarded(value: int | None, status: str) -> None:
        nonlocal last_phase
        guarded_progress(value, status)
        phase = status.partition(":")[0]
        if phase != last_phase:
            _log(log_path, phase)
            last_phase = phase

    guarded(2, "Waiting for application to close...")
    wait_for_process(config.current_pid)
    installers = {
        "linux-appimage": lambda: install_appimage(config, guarded, popen),
        "linux-deb": lambda: install_deb(config, guarded, runner, popen),
        "linux-flatpak": lambda: install_flatpak(config, guarded, runner, popen),
        "macos-bundle": lambda: install_macos(config, guarded, runner, popen),
    }
    try:
        installers[config.strategy]()
        _log(log_path, "Update completed")
    except Exception as exc:
        _log(log_path, f"Update failed: {exc}")
        raise


def run_helper(config_path: Path) -> int:
    from PySide6.QtCore import QObject, QThread, Qt, Signal
    from PySide6.QtWidgets import QApplication, QDialog, QLabel, QProgressBar, QVBoxLayout

    _application = QApplication.instance() or QApplication([])
    dialog = QDialog()
    dialog.setWindowTitle("Application Update")
    dialog.setFixedSize(480, 250)
    dialog.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
    layout = QVBoxLayout(dialog)
    title = QLabel("APPLICATION UPDATE")
    title.setStyleSheet("font-size: 28px; font-weight: bold;")
    title.setAlignment(Qt.AlignmentFlag.AlignCenter)
    status = QLabel("Preparing update...")
    status.setAlignment(Qt.AlignmentFlag.AlignCenter)
    bar = QProgressBar()
    bar.setRange(0, 100)
    bar.setValue(0)
    bar.setTextVisible(True)
    layout.addStretch()
    layout.addWidget(title)
    layout.addWidget(QLabel("Updating...", alignment=Qt.AlignmentFlag.AlignCenter))
    layout.addStretch()
    layout.addWidget(status)
    layout.addWidget(bar)
    layout.addStretch()

    class Worker(QObject):
        changed = Signal(object, str)
        done = Signal()
        failed = Signal(str)

        def run(self):
            try:
                perform_update(HelperConfig.load(config_path), self.changed.emit)
            except Exception as exc:
                self.failed.emit(str(exc))
            else:
                self.done.emit()

    worker = Worker()
    thread = QThread()
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    worker.changed.connect(lambda value, text: (status.setText(text), bar.setRange(0, 0) if value is None else (bar.setRange(0, 100), bar.setValue(value))))
    worker.done.connect(dialog.accept)
    def show_failure(message: str) -> None:
        from PySide6.QtWidgets import QMessageBox

        status.setText("Update failed.")
        bar.setRange(0, 100)
        QMessageBox.critical(dialog, "Application Update", message)
        dialog.reject()

    worker.failed.connect(show_failure)
    worker.done.connect(thread.quit)
    worker.failed.connect(thread.quit)
    dialog.show()
    config_path.with_suffix(".ready").write_text("ready", encoding="ascii")
    thread.start()
    result = dialog.exec()
    thread.wait()
    return 0 if result else 1


if __name__ == "__main__":
    raise SystemExit(run_helper(Path(sys.argv[1])))

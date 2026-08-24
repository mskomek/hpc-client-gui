from __future__ import annotations

import os
import platform
import socket
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Optional

from hpc_gui.core.i18n import t
from hpc_gui.core.paths import app_data_dir, app_log_dir, third_party_dir
from hpc_gui.services.safe_download import download_atomic

from hpc_gui.services.vcxsrv_release_downloader import get_latest_vcxsrv_asset

# Standalone goals:
# - No PuTTY/MobaXterm required (we download plink/vcxsrv with explicit user consent elsewhere).
# - For plink -X to work reliably on Windows, local X server must listen on TCP 127.0.0.1:6000 (DISPLAY :0).
# - VcXsrv must be SINGLE instance; starting a second one often exits immediately with "another window manager".

_LAST_START_TS = 0.0


def _lock_path() -> Path:
    return app_data_dir() / "vcxsrv_start.lock"


def _pid_path() -> Path:
    return app_data_dir() / "vcxsrv_pid.txt"


def _stdout_log_path() -> Path:
    return app_log_dir() / "vcxsrv_stdout.log"


def _stderr_log_path() -> Path:
    return app_log_dir() / "vcxsrv_stderr.log"


def stop_x_server_started_by_app(log: Optional[Callable[[str], None]] = None) -> bool:
    """Stop VcXsrv if it was started by HPC Client GUI.

    We record the PID when we start VcXsrv. If the user runs their own
    X server, we do not attempt to kill it.
    """
    if not _is_windows():
        return False

    try:
        pid_path = _pid_path()
        if not pid_path.exists():
            return False
        pid_s = (pid_path.read_text(encoding="utf-8", errors="ignore") or "").strip()
        pid = int(pid_s)
    except Exception:
        return False

    try:
        _log(log, t("xserver.stopping").format(pid=pid))
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            capture_output=True,
            text=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        try:
            from hpc_gui.services.process_registry import unregister

            unregister(pid)
        except Exception:
            pass
        return True
    finally:
        try:
            pid_path.unlink(missing_ok=True)
        except Exception:
            pass


def _log(log: Optional[Callable[[str], None]], msg: str) -> None:
    if log:
        log(msg)


def _is_windows() -> bool:
    return platform.system().lower() == "windows"


def _is_macos() -> bool:
    return platform.system().lower() == "darwin"


def _is_port_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.25):
            return True
    except Exception:
        return False


def _is_display_listening(display: int = 0) -> bool:
    return _is_port_open("127.0.0.1", 6000 + int(display))


def is_local_x_available(log: Optional[Callable[[str], None]] = None) -> bool:
    """Return True when a usable local X server exists for this platform.

    On Windows this means a VcXsrv-style server already listening on TCP 6000.
    On Linux it means the DISPLAY environment variable is set, which is how a
    desktop X server is normally exposed to the application.
    """
    if _is_windows():
        return _is_display_listening()
    display = os.environ.get("DISPLAY", "").strip()
    if display:
        return True
    _log(log, "X11: DISPLAY ortam degiskeni ayarli degil.")
    return False


def ensure_xquartz_available(
    log: Optional[Callable[[str], None]] = None,
) -> bool:
    """Validate the user-installed XQuartz prerequisites without installing them."""
    if not _is_macos():
        return False
    if not Path("/Applications/Utilities/XQuartz.app").exists():
        _log(log, "X11: XQuartz bulunamadı. https://www.xquartz.org/ adresinden kurun.")
        return False
    if not Path("/opt/X11/bin/xauth").exists():
        _log(log, "X11: XQuartz xauth bulunamadı: /opt/X11/bin/xauth")
        return False
    display = os.environ.get("DISPLAY", "").strip()
    if not display or display in {":0", "localhost:0.0"}:
        _log(log, "X11: XQuartz DISPLAY ortamı kullanılamıyor; XQuartz'u başlatın.")
        return False
    return True


def _vcxsrv_dir() -> Path:
    return third_party_dir() / "vcxsrv"


def _find_xserver_exe(vc_dir: Path) -> Optional[Path]:
    candidates = [
        vc_dir / "runtime" / "vcxsrv.exe",
        vc_dir / "runtime" / "XWin.exe",
        vc_dir / "vcxsrv.exe",
        vc_dir / "XWin.exe",
    ]
    for c in candidates:
        if c.exists():
            return c
    # recursive fallback
    for folder in (vc_dir / "runtime", vc_dir):
        if folder.exists():
            try:
                for p in folder.rglob("vcxsrv.exe"):
                    return p
                for p in folder.rglob("XWin.exe"):
                    return p
            except Exception:
                pass
    return None


def vcxsrv_executable_path() -> Optional[Path]:
    """Return detected local VcXsrv executable path, if available."""
    try:
        return _find_xserver_exe(_vcxsrv_dir())
    except Exception:
        return None


@contextmanager
def _file_lock(path: Path, timeout_s: float = 6.0):
    path.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    fd = None
    while True:
        try:
            fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(str(os.getpid()))
            break
        except FileExistsError:
            if time.time() - t0 > timeout_s:
                raise TimeoutError("vcxsrv start lock timeout")
            time.sleep(0.1)
    try:
        yield
    finally:
        try:
            path.unlink(missing_ok=True)
        except Exception:
            pass


def _download_file(url: str, dest: Path, log: Optional[Callable[[str], None]] = None, parent=None) -> bool:
    progress = None
    try:
        if parent is not None:
            from PySide6.QtWidgets import QProgressDialog
            from PySide6.QtCore import Qt
            progress = QProgressDialog(t("xserver.downloading"), t("common.cancel"), 0, 100, parent)
            progress.setWindowModality(Qt.WindowModality.ApplicationModal)
            progress.setMinimumDuration(0)
            progress.setValue(0)
        def update(downloaded: int, total: int) -> None:
            if total > 0 and progress is not None:
                progress.setValue(min(100, int(downloaded * 100 / total)))
        if not download_atomic(url, dest, cancelled=progress.wasCanceled if progress else None, progress=update):
            _log(log, t("xserver.download_cancelled"))
            return False
        if progress is not None:
            progress.setValue(100)
        return True
    except Exception as e:
        _log(log, t("xserver.download_error").format(err=e))
        return False
    finally:
        if progress is not None:
            progress.close()

def _run_noadmin_installer(installer: Path, target_dir: Path, log: Optional[Callable[[str], None]] = None) -> bool:
    target_dir.mkdir(parents=True, exist_ok=True)
    try:
        cmd = [str(installer), "/S", f"/D={str(target_dir)}"]
        _log(log, t("xserver.install_start").format(exe=cmd[0]))
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        proc = subprocess.run(cmd, capture_output=True, text=True, creationflags=creationflags)
        if proc.returncode != 0:
            _log(log, t("xserver.install_error").format(rc=proc.returncode, stderr=proc.stderr.strip()))
            return False
        return True
    except Exception as e:
        _log(log, t("xserver.install_exception").format(err=e))
        return False


def _prompt_install(parent, log: Optional[Callable[[str], None]] = None) -> bool:
    from PySide6.QtWidgets import QMessageBox

    asset = get_latest_vcxsrv_asset()
    if not asset or not asset.download_url:
        _log(log, t("xserver.release_failed_log"))
        QMessageBox.warning(parent, t("xserver.prompt_title"), t("xserver.version_not_found"))
        return False

    msg = t("xserver.prompt_msg").format(name=asset.name, mb=asset.size/1024/1024)
    ret = QMessageBox.question(parent, t("xserver.required_title"), msg, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    if ret != QMessageBox.StandardButton.Yes:
        return False

    vc_dir = _vcxsrv_dir()
    download_dir = app_data_dir() / "downloads"
    download_dir.mkdir(parents=True, exist_ok=True)
    installer_path = download_dir / asset.name

    _log(log, t("xserver.download_log").format(url=asset.download_url))
    if not _download_file(asset.download_url, installer_path, log=log, parent=parent):
        return False

    runtime_dir = vc_dir / "runtime"
    ret = QMessageBox.question(parent, t("xserver.verify_title"), t("xserver.verify_msg"), QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    if ret != QMessageBox.StandardButton.Yes:
        installer_path.unlink(missing_ok=True)
        _log(log, t("xserver.unverified_cancelled"))
        return False
    if not _run_noadmin_installer(installer_path, runtime_dir, log=log):
        return False

    xexe = _find_xserver_exe(vc_dir)
    if not xexe:
        _log(log, t("xserver.missing_after_install"))
        QMessageBox.warning(parent, t("xserver.prompt_title"), t("xserver.missing_after_install"))
        return False

    _log(log, t("xserver.ready").format(path=xexe))
    return True


def ensure_x_server_running(
    log: Optional[Callable[[str], None]] = None,
    *,
    display: int = 0,
    parent=None,
    allow_download: bool = True,
) -> bool:
    """Return True only if a usable local X server is available.

    On Linux this checks the DISPLAY environment variable (system X server); on
    Windows it requires 127.0.0.1:6000 to be listening (plink requirement).
    """

    if _is_macos():
        return ensure_xquartz_available(log)
    if not _is_windows():
        return is_local_x_available(log)

    # Already good
    if _is_display_listening(display):
        return True

    # Cooldown: avoid start-loop / popup spam
    global _LAST_START_TS
    if time.time() - _LAST_START_TS < 8.0:
        for _ in range(80):  # wait up to 8s for someone else to finish starting
            if _is_display_listening(display):
                return True
            time.sleep(0.1)
        return _is_display_listening(display)

    vc_dir = _vcxsrv_dir()
    xexe = _find_xserver_exe(vc_dir)

    if not xexe:
        _log(log, t("xserver.local_not_found"))
        if allow_download and parent is not None:
            if _prompt_install(parent, log=log):
                xexe = _find_xserver_exe(vc_dir)

    if not xexe:
        _log(log, t("xserver.need_confirm_log"))
        return False

    # Single instance: cross-process lock
    try:
        with _file_lock(_lock_path(), timeout_s=6.0):
            # Someone else might have started it while we waited
            if _is_display_listening(display):
                return True

            # Start VcXsrv with TCP listening (plink requirement).
            # Keep args minimal & stable; invalid args cause help popup (and no server).
            args = [
                str(xexe),
                f":{display}",
                "-multiwindow",
                "-ac",
                "-noreset",
                "-notrayicon",
                "-listen",
                "tcp",
            ]

            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            stdout_path = _stdout_log_path()
            stderr_path = _stderr_log_path()
            stdout_f = open(stdout_path, "ab", buffering=0)
            stderr_f = open(stderr_path, "ab", buffering=0)

            proc = subprocess.Popen(
                args,
                cwd=str(xexe.parent),
                stdout=stdout_f,
                stderr=stderr_f,
                stdin=subprocess.DEVNULL,
                close_fds=False,
                creationflags=creationflags,
            )

            _LAST_START_TS = time.time()
            _log(log, t("xserver.starting").format(name=xexe.name, pid=proc.pid))
            try:
                from hpc_gui.services.process_registry import register

                register(proc.pid, kind="vcxsrv", cmd=" ".join(args))
            except Exception:
                pass
            try:
                _pid_path().write_text(str(proc.pid), encoding="utf-8")
            except Exception:
                # PID recording is best-effort
                pass

            # Wait for TCP 6000
            for _ in range(60):  # 6s
                if _is_display_listening(display):
                    _log(log, t("xserver.ready_listen"))
                    return True
                if proc.poll() is not None:
                    _log(
                        log,
                        t("xserver.start_closed") + "\n" + t("xserver.details_log").format(path=str(_stderr_log_path()))
                    )
                    return False
                time.sleep(0.1)

            _log(
                log,
                t("xserver.port_not_open") + "\n" + t("xserver.details_log").format(path=str(_stderr_log_path()))
            )
            return False

    except TimeoutError:
        _log(log, t("xserver.lock_timeout"))
        return False

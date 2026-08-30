from __future__ import annotations

import os
import platform
import shutil
import socket
import subprocess
import webbrowser
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Optional

from hpc_gui.core.i18n import t
from hpc_gui.core.paths import app_data_dir, app_log_dir

# X11 goals:
# - Third-party executables must be installed by the user from official sources.
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


def vcxsrv_executable_path() -> Optional[Path]:
    """Return a user-installed VcXsrv executable, never an app download cache."""
    candidates = [shutil.which("vcxsrv"), shutil.which("XWin")]
    for env_name in ("ProgramFiles", "ProgramFiles(x86)"):
        root = os.environ.get(env_name)
        if root:
            candidates.extend((str(Path(root) / "VcXsrv" / "vcxsrv.exe"), str(Path(root) / "VcXsrv" / "XWin.exe")))
    return next((Path(value) for value in candidates if value and Path(value).is_file()), None)


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


def _prompt_install(parent, log: Optional[Callable[[str], None]] = None) -> bool:
    from PySide6.QtWidgets import QMessageBox
    msg = "VcXsrv is required. Open its official download page?"
    ret = QMessageBox.question(parent, t("xserver.required_title"), msg, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    if ret != QMessageBox.StandardButton.Yes:
        return False
    webbrowser.open("https://sourceforge.net/projects/vcxsrv/files/vcxsrv/")
    _log(log, "VcXsrv official download page opened; automatic installer execution is disabled.")
    return False


def _vcxsrv_args(executable: Path, display: int) -> list[str]:
    return [
        str(executable), f":{display}", "-multiwindow", "-noreset",
        "-notrayicon", "-listen", "tcp",
    ]


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

    xexe = vcxsrv_executable_path()

    if not xexe:
        _log(log, t("xserver.local_not_found"))
        if allow_download and parent is not None:
            if _prompt_install(parent, log=log):
                xexe = vcxsrv_executable_path()

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
            args = _vcxsrv_args(xexe, display)

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

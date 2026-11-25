from __future__ import annotations

import codecs
import os
import shutil
import subprocess
from threading import Lock, Thread
from typing import Callable

from hpc_gui.core.i18n import t
from hpc_gui.services.putty_manager import ensure_plink_available
from hpc_gui.services.x11_system_ssh import (
    build_x11_launch,
    is_likely_x11_gui_command,
    is_likely_x11_related_command,
    wrap_remote_cmd_clean_env,
)
from hpc_gui.services.xserver_manager import (
    ensure_x_server_running,
    stop_x_server_started_by_app,
)


def _is_windows() -> bool:
    import platform

    return platform.system().lower() == "windows"


def _is_macos() -> bool:
    import platform

    return platform.system().lower() == "darwin"


class X11Runner:
    """Single-responsibility X11 execution manager.

    Handles:
    - dependency preflight (plink + local X server on Windows; system OpenSSH
      + DISPLAY on Linux)
    - command routing for likely X11 commands
    - subprocess lifecycle + cleanup
    """

    def __init__(self, *, log_cb: Callable[[str], None], parent=None, confirm=None):
        self._log = log_cb
        self._parent = parent
        self._confirm = confirm
        self._bg_procs: list[subprocess.Popen] = []
        self._lock = Lock()

    def _system_ssh_available(self) -> bool:
        return shutil.which("ssh") is not None

    def preflight(self, *, enabled: bool, parent=None, allow_download: bool = True) -> bool:
        if not enabled:
            return True
        p = parent or self._parent
        if _is_windows():
            if not ensure_plink_available(log=self._log, parent=p, confirm=self._confirm):
                return False
            if not ensure_x_server_running(self._log, parent=p, allow_download=allow_download, confirm=self._confirm):
                return False
            return True
        if _is_macos():
            if not self._system_ssh_available():
                self._log("X11: macOS sistem OpenSSH istemcisi bulunamadı.")
                return False
            return ensure_x_server_running(self._log, parent=p)
        # Linux: system OpenSSH is required; the local X server is the DISPLAY env.
        if not self._system_ssh_available():
            self._log("X11: sistem OpenSSH istemcisi (ssh) bulunamadi. X11 iletimi icin ssh kurun.")
            return False
        if not ensure_x_server_running(self._log, parent=p):
            return False
        return True

    def should_handle(self, info, cmd: str) -> bool:
        if not info:
            return False
        x11_enabled = bool(getattr(info, "x11_forwarding", False))
        if not x11_enabled:
            return False
        return bool(is_likely_x11_gui_command(cmd) or is_likely_x11_related_command(cmd))

    def run_if_x11(self, info, cmd: str, *, parent=None) -> bool:
        if not self.should_handle(info, cmd):
            return False

        if _is_macos() and getattr(info, "password", None) and not getattr(info, "key_path", None):
            self._log(t("login.x11_macos_password_limit"))
            return True

        p = parent or self._parent
        if not ensure_x_server_running(self._log, parent=p, allow_download=True, confirm=self._confirm):
            self._log("X11: Yerel X server başlatılamadı veya hazır değil.")
            return True

        remote_cmd = wrap_remote_cmd_clean_env(cmd)
        launch = build_x11_launch(
            host=info.host,
            port=info.port,
            user=info.username,
            remote_cmd=remote_cmd,
            trusted=True,
            key_path=(getattr(info, "key_path", None) or None),
            password=(getattr(info, "password", None) or None),
            host_key_policy=(getattr(info, "host_key_policy", "accept-new") or "accept-new"),
        )
        if not launch:
            self._log("X11: install system OpenSSH or PuTTY from its official source.")
            return True

        env = os.environ.copy()
        if not env.get("DISPLAY"):
            env["DISPLAY"] = "localhost:0.0"
        cmd_show = " ".join([launch.program] + launch.display_args)
        try:
            proc = subprocess.Popen(
                [launch.program, *launch.args], env=env,
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if _is_windows() else 0,
            )
        except OSError as exc:
            self._log(t("login.stderr").format(data=str(exc)))
            return True

        with self._lock:
            self._bg_procs.append(proc)
            try:
                from hpc_gui.services.process_registry import register

                register(proc.pid, kind=f"x11_{launch.backend}")
            except Exception:
                pass
        self._log(t("login.x11_started").format(cmd=cmd_show))

        readers = [
            Thread(target=self._read_stream, args=(proc.stdout, False), daemon=True),
            Thread(target=self._read_stream, args=(proc.stderr, True), daemon=True),
        ]
        for reader in readers:
            reader.start()

        def reap():
            code = proc.wait()
            for reader in readers:
                reader.join(timeout=1)
            with self._lock:
                self._bg_procs.remove(proc)
                try:
                    from hpc_gui.services.process_registry import unregister

                    unregister(proc.pid)
                except Exception:
                    pass
            self._log(t("login.x11_finished").format(code=code))

        Thread(target=reap, daemon=True, name="x11-process-reaper").start()
        return True

    def shutdown(self, *, close_x11_procs: bool, close_vcxsrv: bool) -> None:
        if close_x11_procs:
            with self._lock:
                active = list(self._bg_procs)
            for proc in active:
                try:
                    if proc.poll() is None:
                        proc.terminate()
                        try:
                            proc.wait(timeout=1)
                        except subprocess.TimeoutExpired:
                            proc.kill()
                            proc.wait(timeout=1)
                except (OSError, subprocess.TimeoutExpired):
                    # Keep ownership registered until the reaper observes exit.
                    pass

        if close_vcxsrv:
            try:
                stop_x_server_started_by_app(log=self._log)
            except Exception:
                pass

    def _read_stream(self, stream, err: bool) -> None:
        if stream is None:
            return
        decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        from hpc_gui.core.log_redaction import redact_text

        try:
            with stream:
                while True:
                    chunk = stream.read1(4096)
                    data = decoder.decode(chunk, final=not chunk)
                    if data.strip():
                        safe = redact_text(data.rstrip())
                        self._log(t("login.stderr").format(data=safe) if err else safe)
                    if not chunk:
                        break
        except (OSError, ValueError):
            pass

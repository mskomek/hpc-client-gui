from __future__ import annotations

"""Lightweight external process registry.

Purpose
-------
HPC Client GUI may spawn external helper processes (e.g. VcXsrv, plink/ssh for X11).
On Windows, these can be left orphaned if the app crashes or is killed.

This registry is best-effort and **log-only**: it helps cleanup stale records
and optionally terminates known orphan helpers at startup.

No UI is shown from here.
"""

import json
import os
import platform
import subprocess
import tempfile
import time
from pathlib import Path
from threading import RLock
from typing import Any, Dict, Optional

from hpc_gui.core.logging import get_logger
from hpc_gui.core.log_redaction import redact_text
from hpc_gui.core.paths import app_data_dir


_log = get_logger("hpc_gui.proc")
_registry_lock = RLock()


def _registry_path() -> Path:
    return app_data_dir() / "processes.json"


def _is_windows() -> bool:
    return platform.system().lower() == "windows"


def _read_all() -> Dict[str, Any]:
    try:
        path = _registry_path()
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8", errors="replace") or "{}") or {}
    except Exception:
        return {}
    return {}


def _write_all(data: Dict[str, Any]) -> None:
    try:
        path = _registry_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
        temporary = Path(temporary_name)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(redact_text(json.dumps(data, ensure_ascii=False, indent=2)))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        if os.name == "posix":
            path.chmod(0o600)
    except Exception:
        if "temporary" in locals():
            temporary.unlink(missing_ok=True)
        pass


def register(pid: int, *, kind: str, cmd: str = "", meta: Optional[Dict[str, Any]] = None) -> None:
    """Register an externally spawned process."""
    try:
        pid = int(pid)
    except Exception:
        return
    if pid <= 0:
        return
    with _registry_lock:
        data = _read_all()
        data[str(pid)] = {
            "pid": pid,
            "kind": str(kind or ""),
            "cmd": redact_text(str(cmd or "")),
            "meta": json.loads(redact_text(json.dumps(meta or {}, ensure_ascii=False))),
            "ts": int(time.time()),
            "host_pid": os.getpid(),
        }
        _write_all(data)


def unregister(pid: int) -> None:
    try:
        pid = int(pid)
    except Exception:
        return
    with _registry_lock:
        data = _read_all()
        if str(pid) in data:
            data.pop(str(pid), None)
            _write_all(data)


def _pid_exists_windows(pid: int) -> bool | None:
    """Return False only for a confirmed missing/exited process.

    Access denied and query failures are unknown, not proof of absence.
    """
    import ctypes
    from ctypes import wintypes

    try:
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        open_process = kernel.OpenProcess
        open_process.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
        open_process.restype = wintypes.HANDLE
        get_exit_code = kernel.GetExitCodeProcess
        get_exit_code.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
        get_exit_code.restype = wintypes.BOOL
        close_handle = kernel.CloseHandle
        close_handle.argtypes = (wintypes.HANDLE,)
        close_handle.restype = wintypes.BOOL
        handle = open_process(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False if ctypes.get_last_error() == 87 else None
        try:
            code = wintypes.DWORD()
            if not get_exit_code(handle, ctypes.byref(code)):
                return None
            return code.value == 259  # STILL_ACTIVE
        finally:
            close_handle(handle)
    except Exception:
        return None


def _pid_exists(pid: int) -> bool | None:
    if _is_windows():
        return _pid_exists_windows(pid)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except (PermissionError, OSError, OverflowError):
        return None
    return True


def _kill_tree_windows(pid: int) -> None:
    try:
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            capture_output=True,
            text=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except Exception:
        pass


def cleanup_orphans(*, aggressive: bool = False, age_s: int = 2 * 3600) -> None:
    """Cleanup stale records and (optionally) terminate known orphan helpers.

    - Always removes records for PIDs that no longer exist.
    - If aggressive=True on Windows, will taskkill remaining registered PIDs.
      This is intended only for helpers spawned by HPC Client GUI.
    """
    with _registry_lock:
        data = _read_all()
        if not data:
            return

        changed = False
        now = int(time.time())
        for pid_s, rec in list(data.items()):
            try:
                pid = int(pid_s)
            except Exception:
                data.pop(pid_s, None)
                changed = True
                continue

            if pid <= 0:
                data.pop(pid_s, None)
                changed = True
                continue
            exists = _pid_exists(pid)

            if exists is False:
                data.pop(pid_s, None)
                changed = True
                continue

            if aggressive and exists is True and _is_windows():
                kind = str((rec or {}).get("kind") or "")
                ts = int((rec or {}).get("ts") or 0)
                # Be conservative: only kill helpers that look like ours and are "old".
                if kind.startswith("vcxsrv") or kind.startswith("x11_"):
                    if ts and (now - ts) >= max(60, int(age_s)):
                        _log.info(f"orphan cleanup: killing pid={pid} kind={kind}")
                        _kill_tree_windows(pid)
                        data.pop(pid_s, None)
                        changed = True

        if changed:
            _write_all(data)

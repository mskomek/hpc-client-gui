"""Local startup checks; never connect to a remote host or kill a process."""
from __future__ import annotations

import logging


def check_startup_helpers() -> dict[str, bool]:
    """Check importable backend APIs, not remote connection readiness."""
    log = logging.getLogger("hpc_gui.startup")
    result = {"SSH backend": False, "SFTP backend": False}
    try:
        from hpc_gui.ssh.client import SSHClientWrapper

        result["SSH backend"] = callable(SSHClientWrapper.connect)
    except Exception:
        log.exception("SSH backend check failed")
    try:
        from hpc_gui.services.files_ssh import SSHFilesBackend

        result["SFTP backend"] = all(
            callable(getattr(SSHFilesBackend, method, None))
            for method in ("listdir", "upload", "download")
        )
    except Exception:
        log.exception("SFTP backend check failed")
    try:
        from hpc_gui.services.process_registry import cleanup_orphans

        # PID reuse and parallel application instances make killing old PIDs
        # unsafe. Only remove registry records for confirmed-dead processes.
        cleanup_orphans(aggressive=False)
    except Exception:
        log.exception("Stale process record cleanup failed")
    return result

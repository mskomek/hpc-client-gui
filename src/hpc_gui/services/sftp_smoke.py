"""SFTP smoke diagnostics for the ``doctor smoke`` CLI flow.

This service owns the smoke-stage logic. It walks the canonical stage set
(``temp_dir``, ``upload``, ``list``, ``download``, ``checksum``, ``cleanup``) against a files backend and
returns a report dict. It never prints and keeps every stage detail static so no
host, username, key path, or raw exception text leaks out. The remote temp
directory is removed when ``cleanup`` is requested and was actually created;
callers may opt out with ``cleanup=False``.
"""

from __future__ import annotations

import hashlib
import os
import secrets
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Optional

from hpc_gui.services.transfer_mode import download_with_mode, upload_with_mode


STAGES = ("temp_dir", "upload", "list", "download", "checksum", "cleanup")

_REMOTE_FILENAME = "smoke.bin"


def default_temp_dir_name() -> str:
    """Return a deterministic-safe remote temp-directory name.

    The value is a ``truba_smoke_<utc-stamp>_<hex-nonce>`` token carrying no
    host, username, path, or secret material, so it is safe to emit in a report
    payload.
    """
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    return f"truba_smoke_{stamp}_{secrets.token_hex(4)}"


def run_sftp_smoke(
    files,
    *,
    temp_dir_name: Optional[Callable[[], str]] = None,
    local_content: bytes = b"truba-sftp-smoke",
    cleanup: bool = True,
) -> dict[str, Any]:
    """Run the smoke stage matrix and return the report payload.

    ``files`` is a ``FakeFiles``/``SSHFilesBackend``-like backend exposing
    ``mkdir``, ``upload``, ``listdir_entries``, ``download``, ``sha256``, and
    ``remove``. ``temp_dir_name`` overrides the default remote directory-name
    generator so tests can make the run deterministic. ``local_content`` is the
    payload uploaded and then downloaded back for the round-trip check.
    ``cleanup`` requests removal of the remote temp directory when it was
    created (default ``True``).
    """
    stages: dict[str, dict[str, str]] = {
        name: {"status": "not_attempted", "detail": ""} for name in STAGES
    }

    remote_dir = temp_dir_name() if temp_dir_name is not None else default_temp_dir_name()
    remote_file = f"{remote_dir.rstrip('/')}/{_REMOTE_FILENAME}"
    remote_created = False

    def record_cleanup() -> None:
        if not cleanup:
            stages["cleanup"] = {"status": "not_attempted", "detail": "skipped"}
        elif not remote_created:
            stages["cleanup"] = {"status": "not_attempted", "detail": "no temp directory"}
        else:
            try:
                files.remove(remote_dir, recursive=True)
            except Exception:
                stages["cleanup"] = {"status": "FAIL", "detail": "cleanup failed"}
            else:
                stages["cleanup"] = {"status": "PASS", "detail": "removed"}

    def fail(stage_index: int, name: str, detail: str) -> dict[str, Any]:
        stages[name] = {"status": "FAIL", "detail": detail}
        for later in STAGES[stage_index + 1 : 5]:
            stages[later] = {"status": "not_attempted", "detail": ""}
        record_cleanup()
        return {"status": "FAIL", "temp_dir": remote_dir, "stages": stages}

    try:
        files.mkdir(remote_dir)
    except Exception:
        return fail(0, "temp_dir", "could not create temp directory")
    remote_created = True
    stages["temp_dir"] = {"status": "PASS", "detail": "created"}

    local_path = ""
    try:
        with tempfile.NamedTemporaryFile(delete=False) as temp:
            temp.write(local_content)
            local_path = temp.name
        upload_with_mode(files, local_path, remote_file, "binary")
        stages["upload"] = {"status": "PASS", "detail": "uploaded"}
    except Exception:
        return fail(1, "upload", "upload failed")
    finally:
        if local_path:
            try:
                os.unlink(local_path)
            except OSError:
                pass

    try:
        entries = files.listdir_entries(remote_dir)
    except Exception:
        return fail(2, "list", "could not list temp directory")
    if not any(getattr(entry, "name", "") == _REMOTE_FILENAME for entry in entries):
        return fail(2, "list", "uploaded file not listed")
    stages["list"] = {"status": "PASS", "detail": "present"}

    dest_path = ""
    try:
        try:
            fd, dest_path = tempfile.mkstemp()
            os.close(fd)
            download_with_mode(files, remote_file, dest_path, "binary")
            downloaded = Path(dest_path).read_bytes()
        except Exception:
            return fail(3, "download", "download failed")
        if downloaded != local_content:
            return fail(3, "download", "content mismatch")
        stages["download"] = {"status": "PASS", "detail": "verified"}
    finally:
        if dest_path:
            try:
                os.unlink(dest_path)
            except OSError:
                pass

    try:
        remote_hex = files.sha256(remote_file)
    except Exception:
        return fail(4, "checksum", "checksum failed")
    if remote_hex.lower() != hashlib.sha256(local_content).hexdigest():
        return fail(4, "checksum", "checksum mismatch")
    stages["checksum"] = {"status": "PASS", "detail": "verified"}

    record_cleanup()
    overall = "PASS" if all(stages[name]["status"] == "PASS" for name in STAGES) else "FAIL"
    return {"status": overall, "temp_dir": remote_dir, "stages": stages}

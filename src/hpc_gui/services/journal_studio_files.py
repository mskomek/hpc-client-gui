"""Loss-aware local and SFTP persistence for Journal Studio."""

from __future__ import annotations

import hashlib
from pathlib import Path, PurePosixPath
import stat as stat_module
from threading import RLock
import uuid
from weakref import WeakKeyDictionary

from hpc_gui.journal_studio.codec import MAX_JOURNAL_BYTES
from hpc_gui.journal_studio.document import JournalConflictError, write_local_atomic

_pending_temp_lock = RLock()
_pending_remote_temps: WeakKeyDictionary[object, set[str]] = WeakKeyDictionary()


def read_local(path: str | Path) -> bytes:
    target = Path(path)
    if target.is_symlink():
        raise OSError("Refusing to open a symbolic link as a journal")
    size = target.stat().st_size
    if size > MAX_JOURNAL_BYTES:
        raise ValueError("Journal exceeds the 128 MiB editing limit")
    return target.read_bytes()


def _remote_path(path: str) -> str:
    if not isinstance(path, str) or not path.startswith("/") or "\x00" in path or "\\" in path:
        raise ValueError("Remote journal path must be an absolute POSIX path")
    normalized = PurePosixPath(path)
    if ".." in normalized.parts:
        raise ValueError("Remote journal path cannot contain '..'")
    return str(normalized)


def _sftp_for(files_backend):
    ssh = getattr(files_backend, "ssh", None)
    opener = getattr(ssh, "open_transfer_sftp", None)
    if not callable(opener):
        raise RuntimeError("The active connection does not provide SFTP transfers")
    sftp = opener()
    _cleanup_pending_remote_temps(ssh, sftp)
    return sftp


def _remember_pending_remote_temp(ssh, path: str) -> None:
    """Remember only this process's temp path when a disconnected SFTP blocks cleanup."""
    try:
        with _pending_temp_lock:
            _pending_remote_temps.setdefault(ssh, set()).add(path)
    except TypeError:
        # Some third-party SSH wrappers are not weak-referenceable/hashable.
        # Their failed temp file remains hidden and isolated to the target folder.
        pass


def _cleanup_pending_remote_temps(ssh, sftp) -> None:
    """Retry cleanup for exact temporary paths created by this live process."""
    try:
        with _pending_temp_lock:
            pending = tuple(_pending_remote_temps.get(ssh, ()))
    except TypeError:
        return
    for path in pending:
        try:
            _reject_remote_symlinks(sftp, path)
            sftp.remove(path)
        except FileNotFoundError:
            cleaned = True
        except OSError as exc:
            cleaned = getattr(exc, "errno", None) == 2
        except Exception:
            cleaned = False
        else:
            cleaned = True
        if cleaned:
            with _pending_temp_lock:
                paths = _pending_remote_temps.get(ssh)
                if paths is not None:
                    paths.discard(path)
                    if not paths:
                        _pending_remote_temps.pop(ssh, None)


def _reject_remote_symlinks(sftp, target: str) -> None:
    """Reject symlinked path components before reading or replacing a journal."""
    parts = PurePosixPath(target).parts
    current = ""
    for index, part in enumerate(parts):
        if part == "/":
            current = "/"
            continue
        current = f"{current.rstrip('/')}/{part}"
        try:
            attributes = sftp.lstat(current)
        except FileNotFoundError:
            # A missing leaf is valid for Save As. Missing parents will fail on
            # the subsequent operation without following another path.
            if index < len(parts) - 1:
                return
            return
        mode = int(getattr(attributes, "st_mode", 0) or 0)
        if stat_module.S_ISLNK(mode):
            raise OSError(f"Refusing to access a journal through a symbolic link: {current}")
        if index < len(parts) - 1 and not stat_module.S_ISDIR(mode):
            raise NotADirectoryError(current)


def _close_quietly(sftp) -> None:
    """Cleanup after a failed transfer must not replace the transfer's own error."""
    try:
        sftp.close()
    except Exception:
        pass


def _remote_snapshot(sftp, target: str):
    try:
        stat = sftp.stat(target)
    except FileNotFoundError:
        # Only a genuine missing file means "absent"; a dropped connection must surface as-is.
        return False, None, None
    with sftp.open(target, "rb") as source:
        data = bytes(source.read(MAX_JOURNAL_BYTES + 1))
    if len(data) > MAX_JOURNAL_BYTES:
        raise ValueError("Remote journal exceeds the 128 MiB editing limit")
    return True, stat, hashlib.sha256(data).hexdigest()


def read_remote(files_backend, path: str) -> bytes:
    target = _remote_path(path)
    sftp = _sftp_for(files_backend)
    try:
        _reject_remote_symlinks(sftp, target)
        stat = sftp.stat(target)
        size = int(getattr(stat, "st_size", 0) or 0)
        if size > MAX_JOURNAL_BYTES:
            raise ValueError("Journal exceeds the 128 MiB editing limit")
        with sftp.open(target, "rb") as handle:
            data = bytes(handle.read(MAX_JOURNAL_BYTES + 1))
        if len(data) > MAX_JOURNAL_BYTES:
            raise ValueError("Journal exceeds the 128 MiB editing limit")
        return data
    finally:
        _close_quietly(sftp)


def save_remote(files_backend, path: str, data: bytes, *, expected_sha256: str | None) -> str:
    """Upload, verify, then rename a same-directory temporary file into place."""
    target = _remote_path(path)
    if len(data) > MAX_JOURNAL_BYTES:
        raise ValueError("Journal exceeds the 128 MiB editing limit")
    sftp = _sftp_for(files_backend)
    ssh = getattr(files_backend, "ssh", None)
    temporary = str(PurePosixPath(target).parent / f".{PurePosixPath(target).name}.{uuid.uuid4().hex}.journal-tmp")
    temporary_attempted = False
    committed = False
    try:
        _reject_remote_symlinks(sftp, target)
        exists, current_stat, current_digest = _remote_snapshot(sftp, target)
        if exists:
            if expected_sha256 is None or current_digest != expected_sha256:
                raise JournalConflictError("The remote file changed after it was opened. Compare or reopen before saving.")
        elif expected_sha256 is not None:
            raise JournalConflictError("The remote file was removed after it was opened. Save As to keep your edits.")

        temporary_attempted = True
        with sftp.open(temporary, "wb") as destination:
            destination.write(data)
            flush = getattr(destination, "flush", None)
            if callable(flush):
                flush()
        with sftp.open(temporary, "rb") as check:
            uploaded = bytes(check.read(MAX_JOURNAL_BYTES + 1))
        if uploaded != data:
            raise IOError("Remote upload verification failed; original file was left in place")
        _reject_remote_symlinks(sftp, target)
        exists_now, _latest_stat, latest_digest = _remote_snapshot(sftp, target)
        if exists:
            if not exists_now or latest_digest != expected_sha256:
                raise JournalConflictError("The remote file changed during upload. The uploaded temporary file was removed.")
        elif exists_now:
            raise JournalConflictError("A remote file was created during upload. The uploaded temporary file was removed.")
        if exists:
            mode = int(getattr(current_stat, "st_mode", 0) or 0) & 0o777
            if mode:
                sftp.chmod(temporary, mode)
            replace = getattr(sftp, "posix_rename", None)
            if not callable(replace):
                raise RuntimeError("The SFTP server does not support atomic replacement; remote save was stopped")
            replace(temporary, target)
        else:
            # The SFTP rename operation must fail if the destination already exists.
            sftp.rename(temporary, target)
        committed = True
        return hashlib.sha256(data).hexdigest()
    finally:
        try:
            sftp.remove(temporary)
        except Exception:
            if temporary_attempted and not committed:
                _remember_pending_remote_temp(ssh, temporary)
        _close_quietly(sftp)


def save_local(path: str | Path, data: bytes, *, expected_sha256: str | None) -> str:
    return write_local_atomic(path, data, expected_sha256=expected_sha256)

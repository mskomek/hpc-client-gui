from __future__ import annotations

import contextlib
import errno
import os
import re
import stat as pystat
from typing import Iterator, List, Tuple

from hpc_gui.services.files_base import FilesBackend, RemoteEntry

_SFTP_CHUNK_SIZE = 8 * 1024 * 1024
_SFTP_PREFETCH_REQUESTS = 64
# Paramiko's documented default; enough to keep the pipe full for most
# directories. Raise only against a measured TRUBA baseline.
_LISTDIR_READ_AHEADS = 50


def _enable_sftp_read_ahead(stream, file_size: int) -> None:
    prefetch = getattr(stream, "prefetch", None)
    if callable(prefetch):
        try:
            prefetch(file_size=file_size, max_concurrent_requests=_SFTP_PREFETCH_REQUESTS)
        except TypeError:
            prefetch(file_size)

def _enable_sftp_pipelining(stream) -> None:
    pipelined = getattr(stream, "set_pipelined", None)
    if callable(pipelined):
        pipelined(True)
from hpc_gui.ssh.client import SSHClientWrapper


@contextlib.contextmanager
def _translate_remote_errors(remote_path: str):
    """Re-raise a typed FileNotFoundError/PermissionError with `remote_path`
    attached as `.filename`, so callers always get a path-bearing message
    instead of paramiko's bare `[Errno N] ...` text."""
    try:
        yield
    except (FileNotFoundError, PermissionError) as exc:
        raise type(exc)(exc.errno, exc.strerror or str(exc), remote_path) from exc


_QUOTED_PATH_RE = re.compile(r"'([^']+)'")


def _raise_on_failed_run(code: int, err: str, operation: str, path: str | None = None) -> None:
    """Translate a remote shell result into a typed failure.

    A socket timeout in ``SSHClientWrapper.run`` surfaces as exit code 124;
    surface that as ``TimeoutError`` so the CLI can route it to ``TIMEOUT``.

    When `path` is given, classify a non-zero, non-timeout failure as
    ``FileNotFoundError``/``PermissionError`` by matching well-known GNU
    coreutils stderr wording, attaching whichever path the stderr text
    quotes (falling back to `path` itself when the text quotes nothing) as
    ``.filename`` so the CLI can render a path-bearing message. Omitting
    `path` preserves today's plain ``RuntimeError`` behavior exactly.
    """
    if code == 124:
        raise TimeoutError(f"{operation} timed out")
    if code == 0:
        return
    text = err.strip() or f"{operation} failed (exit={code})"
    if path is not None:
        lowered = text.lower()
        match = _QUOTED_PATH_RE.search(text)
        reported_path = match.group(1) if match else path
        if "no such file or directory" in lowered:
            raise FileNotFoundError(errno.ENOENT, text, reported_path)
        if "permission denied" in lowered:
            raise PermissionError(errno.EACCES, text, reported_path)
    raise RuntimeError(text)


class SSHFilesBackend(FilesBackend):
    supports_progressive_listing = True
    def __init__(self, ssh: SSHClientWrapper):
        if not ssh.sftp:
            raise RuntimeError("SFTP not available")
        self.ssh = ssh
        # Construction happens in the connection worker.  Cache the channel
        # capability here so opening a transfer controller never performs an
        # SSH round trip on the Qt GUI thread.
        capability_probe = getattr(ssh, "supports_transfer_sftp_channels", None)
        self._supports_parallel_transfers = bool(
            capability_probe()
        ) if callable(capability_probe) else False

        # Edge-case notes (for maintainers):
        # - NFS "stale file handle" can occur after scratch purge; operations may fail
        #   even if paths look valid.
        # - Quota can be exceeded even when `df -h` looks fine (home/scratch policies).
        # - Permission issues can be subtle (directory has r/w but missing execute bit).

    @property
    def supports_parallel_transfers(self) -> bool:
        """Whether this connection can create an SFTP channel per transfer."""
        return self._supports_parallel_transfers

    def listdir(self, remote_dir: str) -> List[str]:
        with _translate_remote_errors(remote_dir):
            return self.ssh.sftp.listdir(remote_dir)

    @staticmethod
    def _entry_from_attr(remote_dir: str, attr) -> RemoteEntry:
        name = getattr(attr, "filename", "") or ""
        mode = getattr(attr, "st_mode", 0) or 0
        return RemoteEntry(
            name=name,
            path=remote_dir.rstrip("/") + "/" + name,
            is_dir=pystat.S_ISDIR(mode),
            size=int(getattr(attr, "st_size", 0) or 0),
            mtime=int(getattr(attr, "st_mtime", 0) or 0),
            mode=mode,
        )

    def iterdir_entries(self, remote_dir: str) -> Iterator[RemoteEntry]:
        """Stream a directory over the shared listing channel.

        ``listdir_iter`` keeps several READDIR requests in flight, so entries
        surface while the server is still walking the directory instead of
        after the whole listing lands.  Unsorted by design: the caller renders
        in arrival order and sorts once at the end.
        """
        with self.ssh.listing_sftp() as sftp:
            with _translate_remote_errors(remote_dir):
                for attr in sftp.listdir_iter(remote_dir, read_aheads=_LISTDIR_READ_AHEADS):
                    yield self._entry_from_attr(remote_dir, attr)

    def listdir_entries(self, remote_dir: str) -> List[RemoteEntry]:
        entries: List[RemoteEntry] = []
        listing_sftp = self.ssh.sftp
        opener = getattr(self.ssh, "open_transfer_sftp", None)
        if callable(opener):
            try:
                listing_sftp = opener()
            except Exception:
                listing_sftp = self.ssh.sftp
        if listing_sftp is None:
            raise RuntimeError("SFTP channel is not available")
        isolated_sftp = listing_sftp is not self.ssh.sftp
        try:
            with _translate_remote_errors(remote_dir):
                for attr in listing_sftp.listdir_attr(remote_dir):
                    name = getattr(attr, "filename", "") or ""
                    path = remote_dir.rstrip("/") + "/" + name
                    mode = getattr(attr, "st_mode", 0) or 0
                    is_dir = pystat.S_ISDIR(mode)
                    size = int(getattr(attr, "st_size", 0) or 0)
                    mtime = int(getattr(attr, "st_mtime", 0) or 0)
                    entries.append(RemoteEntry(
                        name=name, path=path, is_dir=is_dir, size=size, mtime=mtime, mode=mode
                    ))
        finally:
            if isolated_sftp:
                listing_sftp.close()
        entries.sort(key=lambda e: (not e.is_dir, e.name.lower()))
        return entries
    def read_text(self, remote_path: str) -> str:
        sftp = self.ssh.open_transfer_sftp()
        try:
            with sftp.open(remote_path, "rb") as f:
                data = f.read()
            return data.decode("utf-8", errors="replace")
        finally:
            sftp.close()

    def write_text(self, remote_path: str, text: str) -> None:
        with self.ssh.sftp.open(remote_path, "wb") as f:
            f.write(text.encode("utf-8"))

    def stat(self, remote_path: str) -> Tuple[int, int]:
        with _translate_remote_errors(remote_path):
            st = self.ssh.sftp.stat(remote_path)
        return int(getattr(st, "st_size", 0) or 0), int(getattr(st, "st_mtime", 0) or 0)

    def stat_entry(self, remote_path: str) -> RemoteEntry:
        """Return a full remote entry (six fields) for a single path.

        Mirrors the fields ``listdir_entries`` emits so ``files stat`` and
        ``files ls`` stay metadata-parity for callers like the CLI.
        """
        with _translate_remote_errors(remote_path):
            st = self.ssh.sftp.stat(remote_path)
        mode = int(getattr(st, "st_mode", 0) or 0)
        return RemoteEntry(
            name=os.path.basename(remote_path.rstrip("/")) or "/",
            path=remote_path,
            is_dir=pystat.S_ISDIR(mode),
            size=int(getattr(st, "st_size", 0) or 0),
            mtime=int(getattr(st, "st_mtime", 0) or 0),
            mode=mode,
        )

    def download(self, remote_path: str, local_path: str, progress_cb=None) -> None:
        self._download(remote_path, local_path, progress_cb)

    def resume_download(self, remote_path: str, local_path: str, progress_cb=None) -> None:
        self._download(remote_path, local_path, progress_cb)

    def _download(self, remote_path: str, local_path: str, progress_cb=None) -> None:
        """Download a remote file.

        Resume behavior:
        - If local_path exists and is smaller than the remote size, resume from local size.
        - If sizes match, do nothing.
        - Otherwise, overwrite.
        """
        sftp = self.ssh.open_transfer_sftp()
        try:
            with _translate_remote_errors(remote_path):
                remote_size = int(getattr(sftp.stat(remote_path), "st_size", 0) or 0)
            local_size = 0
            try:
                local_size = os.path.getsize(local_path)
            except Exception:
                local_size = 0

            if local_size == remote_size and remote_size > 0:
                if progress_cb is not None:
                    progress_cb(remote_size, remote_size)
                return

            # Resume only when local is a strict prefix of remote.
            if 0 < local_size < remote_size:
                if progress_cb is not None:
                    progress_cb(local_size, remote_size)
                with sftp.open(remote_path, "rb") as rf:
                    rf.seek(local_size)
                    _enable_sftp_read_ahead(rf, remote_size)
                    os.makedirs(os.path.dirname(local_path) or ".", exist_ok=True)
                    with open(local_path, "ab") as lf:
                        while True:
                            chunk = rf.read(_SFTP_CHUNK_SIZE)
                            if not chunk:
                                break
                            lf.write(chunk)
                            local_size += len(chunk)
                            if progress_cb is not None:
                                progress_cb(local_size, remote_size)
                return

            # Overwrite
            os.makedirs(os.path.dirname(local_path) or ".", exist_ok=True)
            downloaded = 0
            with sftp.open(remote_path, "rb") as rf:
                _enable_sftp_read_ahead(rf, remote_size)
                with open(local_path, "wb") as lf:
                    while True:
                        chunk = rf.read(_SFTP_CHUNK_SIZE)
                        if not chunk:
                            break
                        lf.write(chunk)
                        downloaded += len(chunk)
                        if progress_cb is not None:
                            progress_cb(downloaded, remote_size)
        finally:
            try:
                sftp.close()
            except Exception:
                pass

    def upload(self, local_path: str, remote_path: str, progress_cb=None) -> None:
        self._upload(local_path, remote_path, progress_cb)

    def resume_upload(self, local_path: str, remote_path: str, progress_cb=None) -> None:
        self._upload(local_path, remote_path, progress_cb)

    def _upload(self, local_path: str, remote_path: str, progress_cb=None) -> None:
        """Upload a local file.

        Resume behavior:
        - If remote_path exists and is smaller than the local size, resume from remote size.
        - If sizes match, do nothing.
        - Otherwise, overwrite.
        """
        sftp = self.ssh.open_transfer_sftp()
        try:
            local_size = os.path.getsize(local_path)
            remote_size = 0
            try:
                remote_size = int(getattr(sftp.stat(remote_path), "st_size", 0) or 0)
            except Exception:
                remote_size = 0

            if remote_size == local_size and local_size > 0:
                if progress_cb is not None:
                    progress_cb(local_size, local_size)
                return

            # Resume only when remote is a strict prefix of local.
            if 0 < remote_size < local_size:
                if progress_cb is not None:
                    progress_cb(remote_size, local_size)
                with open(local_path, "rb") as lf:
                    lf.seek(remote_size)
                    with sftp.open(remote_path, "ab") as rf:
                        _enable_sftp_pipelining(rf)
                        while True:
                            chunk = lf.read(1024 * 1024)
                            if not chunk:
                                break
                            rf.write(chunk)
                            remote_size += len(chunk)
                            if progress_cb is not None:
                                progress_cb(remote_size, local_size)
                return

            # Overwrite
            sent = 0
            with open(local_path, "rb") as lf:
                with sftp.open(remote_path, "wb") as rf:
                    _enable_sftp_pipelining(rf)
                    while True:
                        chunk = lf.read(1024 * 1024)
                        if not chunk:
                            break
                        rf.write(chunk)
                        sent += len(chunk)
                        if progress_cb is not None:
                            progress_cb(sent, local_size)
        finally:
            try:
                sftp.close()
            except Exception:
                pass

    def upload_and_rename(self, local_path: str, temporary_path: str, remote_path: str, progress_cb=None) -> None:
        sftp = self.ssh.open_transfer_sftp()
        try:
            local_size = os.path.getsize(local_path)
            with open(local_path, "rb") as source, sftp.open(temporary_path, "wb") as target:
                _enable_sftp_pipelining(target)
                sent = 0
                while chunk := source.read(_SFTP_CHUNK_SIZE):
                    target.write(chunk)
                    sent += len(chunk)
                    if progress_cb is not None:
                        progress_cb(sent, local_size)
            sftp.rename(temporary_path, remote_path)
        finally:
            sftp.close()

    def remove(self, remote_path: str, recursive: bool = False) -> None:
        # Use shell rm to support recursive deletes reliably.
        # remote_path is user-provided via UI; quote defensively.
        import shlex
        q = shlex.quote(remote_path)
        cmd = f"rm {'-rf' if recursive else '-f'} {q}"
        code, _, err = self.ssh.run(cmd)
        _raise_on_failed_run(code, err, "rm", path=remote_path)

    def rename(self, remote_path: str, new_remote_path: str) -> None:
        # Prefer SFTP rename (atomic on many servers)
        self.ssh.sftp.rename(remote_path, new_remote_path)

    def mkdir(self, remote_dir: str) -> None:
        import shlex
        q = shlex.quote(remote_dir)
        code, _, err = self.ssh.run(f"mkdir -p {q}")
        _raise_on_failed_run(code, err, "mkdir")

    def chmod(self, remote_path: str, mode: int) -> None:
        try:
            self.ssh.sftp.chmod(remote_path, mode)
            return
        except Exception:
            pass
        import shlex
        q = shlex.quote(remote_path)
        code, _, err = self.ssh.run(f"chmod {mode:03o} {q}")
        _raise_on_failed_run(code, err, "chmod")

    def exists(self, remote_path: str) -> bool:
        try:
            self.ssh.sftp.stat(remote_path)
            return True
        except Exception:
            return False

    def sha256(self, remote_path: str) -> str:
        """Return the remote file's SHA-256 using the SSH host utility."""
        import shlex

        code, out, err = self.ssh.run(f"sha256sum -- {shlex.quote(remote_path)}")
        _raise_on_failed_run(code, err, "sha256sum", path=remote_path)
        digest = str(out or "").strip().split()[0] if str(out or "").strip() else ""
        if len(digest) != 64:
            raise RuntimeError("Remote sha256sum returned an invalid digest")
        return digest.lower()

    def is_dir(self, remote_path: str) -> bool:
        try:
            st = self.ssh.sftp.stat(remote_path)
            return pystat.S_ISDIR(getattr(st, "st_mode", 0) or 0)
        except Exception:
            return False

    def copy(self, src_remote_path: str, dst_remote_path: str, recursive: bool = False) -> None:
        import shlex
        s = shlex.quote(src_remote_path)
        d = shlex.quote(dst_remote_path)
        cmd = f"cp {'-r' if recursive else ''} {s} {d}".strip()
        code, _, err = self.ssh.run(cmd)
        _raise_on_failed_run(code, err, "cp", path=src_remote_path)

    def move(self, src_remote_path: str, dst_remote_path: str) -> None:
        import shlex
        s = shlex.quote(src_remote_path)
        d = shlex.quote(dst_remote_path)
        code, _, err = self.ssh.run(f"mv {s} {d}")
        _raise_on_failed_run(code, err, "mv", path=src_remote_path)

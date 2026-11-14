"""Server-backed FTP backend used by the loopback transfer stress harness.

Split out of ftp_transfer_stress.py so the harness entrypoint stays small and
the backend can be reused by other loopback measurements.
"""

from __future__ import annotations

import ftplib
import os
import posixpath
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from hpc_gui.services.files_base import RemoteEntry


class ConcurrencyTracker:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.active = 0
        self.maximum = 0

    @contextmanager
    def transfer(self) -> Iterator[None]:
        with self._lock:
            self.active += 1
            self.maximum = max(self.maximum, self.active)
        try:
            yield
        finally:
            with self._lock:
                self.active -= 1


class LoopbackFtpBackend:
    """Minimal server-backed backend; every operation uses a fresh connection."""

    supports_parallel_transfers = True

    def __init__(self, host: str, port: int, username: str, password: str) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.tracker = ConcurrencyTracker()
        self.connection_count = 0
        self._connection_lock = threading.Lock()

    @contextmanager
    def _ftp(self) -> Iterator[ftplib.FTP]:
        ftp = ftplib.FTP(encoding="utf-8")
        ftp.connect(self.host, self.port, timeout=30)
        ftp.login(self.username, self.password)
        try:
            ftp.sendcmd("OPTS UTF8 ON")
        except ftplib.all_errors:
            pass
        with self._connection_lock:
            self.connection_count += 1
        try:
            yield ftp
        finally:
            try:
                ftp.quit()
            except Exception:
                ftp.close()

    @staticmethod
    def _path(path: str) -> str:
        normalized = posixpath.normpath("/" + str(path or "/").lstrip("/"))
        if not normalized.startswith("/"):
            raise ValueError(f"unsafe remote path: {path}")
        return normalized

    def exists(self, remote_path: str) -> bool:
        path = self._path(remote_path)
        with self._ftp() as ftp:
            try:
                ftp.voidcmd(f"MLST {path}")
                return True
            except ftplib.error_perm:
                return False

    def is_dir(self, remote_path: str) -> bool:
        path = self._path(remote_path)
        with self._ftp() as ftp:
            try:
                ftp.cwd(path)
                return True
            except ftplib.error_perm:
                return False

    def mkdir(self, remote_dir: str) -> None:
        path = self._path(remote_dir)
        with self._ftp() as ftp:
            try:
                ftp.mkd(path)
            except ftplib.error_perm as exc:
                if not str(exc).startswith("550 File exists"):
                    raise

    def listdir(self, remote_dir: str) -> list[str]:
        return [entry.name for entry in self.listdir_entries(remote_dir)]

    def listdir_entries(self, remote_dir: str) -> list[RemoteEntry]:
        base = self._path(remote_dir)
        entries: list[RemoteEntry] = []
        with self._ftp() as ftp:
            for name, facts in ftp.mlsd(base):
                if name in {".", ".."}:
                    continue
                is_dir = facts.get("type") == "dir"
                entries.append(
                    RemoteEntry(
                        name=name,
                        path=posixpath.join(base.rstrip("/"), name) or "/",
                        is_dir=is_dir,
                        size=int(facts.get("size", "0")) if not is_dir else 0,
                    )
                )
        return entries

    def upload(self, local_path: str, remote_path: str, progress_cb=None) -> None:
        total = os.path.getsize(local_path)
        done = 0
        with self.tracker.transfer(), self._ftp() as ftp, open(local_path, "rb") as source:
            def on_block(block: bytes) -> None:
                nonlocal done
                done += len(block)
                if progress_cb is not None:
                    progress_cb(done, total)

            ftp.storbinary(f"STOR {self._path(remote_path)}", source, blocksize=1024 * 1024, callback=on_block)

    def download(self, remote_path: str, local_path: str, progress_cb=None) -> None:
        destination = Path(local_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with self.tracker.transfer(), self._ftp() as ftp:
            ftp.voidcmd("TYPE I")
            total = int(ftp.size(self._path(remote_path)) or 0)
            done = 0
            with destination.open("wb") as target:
                def on_block(block: bytes) -> None:
                    nonlocal done
                    target.write(block)
                    done += len(block)
                    if progress_cb is not None:
                        progress_cb(done, total)

                ftp.retrbinary(f"RETR {self._path(remote_path)}", on_block, blocksize=1024 * 1024)

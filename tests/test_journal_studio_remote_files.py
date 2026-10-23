from __future__ import annotations

import hashlib
from io import BytesIO
import stat
from types import SimpleNamespace

import pytest

from hpc_gui.journal_studio.document import JournalConflictError
from hpc_gui.services.journal_studio_files import read_remote, save_remote


class _RemoteFile(BytesIO):
    def __init__(self, owner, path, mode):
        self.owner, self.path, self.mode = owner, path, mode
        super().__init__(owner.files.get(path, b"") if "r" in mode else b"")

    def __exit__(self, *_args):
        if "w" in self.mode:
            self.owner.files[self.path] = self.getvalue()
        self.close()


class _SFTP:
    def __init__(self, files):
        self.files = files
        self.symlinks = set()

    def stat(self, path):
        if path not in self.files:
            raise FileNotFoundError(path)
        return SimpleNamespace(st_size=len(self.files[path]), st_mode=0o100640)

    def lstat(self, path):
        if path in self.symlinks:
            return SimpleNamespace(st_size=0, st_mode=stat.S_IFLNK | 0o777)
        if path in self.files:
            return SimpleNamespace(st_size=len(self.files[path]), st_mode=0o100640)
        if path == "/" or any(item.startswith(path.rstrip("/") + "/") for item in self.files):
            return SimpleNamespace(st_size=0, st_mode=stat.S_IFDIR | 0o700)
        raise FileNotFoundError(path)

    def open(self, path, mode):
        return _RemoteFile(self, path, mode)

    def chmod(self, _path, _mode):
        return None

    def posix_rename(self, source, target):
        self.files[target] = self.files.pop(source)

    def rename(self, source, target):
        if target in self.files:
            raise FileExistsError(target)
        self.files[target] = self.files.pop(source)

    def remove(self, path):
        self.files.pop(path, None)

    def close(self):
        return None


class _FilesBackend:
    def __init__(self, files):
        self.sftp = _SFTP(files)
        self.ssh = SimpleNamespace(open_transfer_sftp=lambda: self.sftp)


def test_remote_save_uses_verified_temporary_then_atomic_replace():
    original = b"/solve/iterate 10\r\n"
    backend = _FilesBackend({"/work/run.jou": original})
    assert read_remote(backend, "/work/run.jou") == original
    updated = b"/solve/iterate 20\r\n"
    result = save_remote(
        backend, "/work/run.jou", updated,
        expected_sha256=hashlib.sha256(original).hexdigest(),
    )
    assert result == hashlib.sha256(updated).hexdigest()
    assert backend.sftp.files == {"/work/run.jou": updated}


def test_remote_conflict_leaves_original_untouched():
    original = b"original"
    backend = _FilesBackend({"/work/run.jou": original})
    with pytest.raises(JournalConflictError):
        save_remote(backend, "/work/run.jou", b"edit", expected_sha256="0" * 64)
    assert backend.sftp.files == {"/work/run.jou": original}


def test_remote_path_traversal_is_rejected_before_open():
    backend = _FilesBackend({})
    with pytest.raises(ValueError):
        read_remote(backend, "/work/../outside.jou")


def test_remote_read_and_save_reject_symlinked_journal_paths():
    backend = _FilesBackend({"/work/original.jou": b"original"})
    backend.sftp.symlinks.add("/work/link.jou")

    with pytest.raises(OSError, match="symbolic link"):
        read_remote(backend, "/work/link.jou")
    with pytest.raises(OSError, match="symbolic link"):
        save_remote(backend, "/work/link.jou", b"replacement", expected_sha256=None)

    assert backend.sftp.files == {"/work/original.jou": b"original"}

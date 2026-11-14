"""SFTP lstat metadata preserves symlink identity without following it."""

from __future__ import annotations

import errno
import stat
from types import SimpleNamespace

import pytest

from hpc_gui.services.files_ssh import SSHFilesBackend


pytestmark = pytest.mark.unit


def _backend():
    calls = []
    def stat_path(path):
        calls.append(("stat", path))
        return SimpleNamespace(st_mode=stat.S_IFDIR | 0o755, st_size=4096, st_mtime=99)

    def lstat_path(path):
        calls.append(("lstat", path))
        return SimpleNamespace(st_mode=stat.S_IFLNK | 0o777, st_size=12, st_mtime=45)

    sftp = SimpleNamespace(stat=stat_path, lstat=lstat_path)
    backend = object.__new__(SSHFilesBackend)
    backend.ssh = SimpleNamespace(sftp=sftp)
    return backend, calls


def test_lstat_entry_returns_link_metadata_without_following_target():
    backend, calls = _backend()
    item = backend.lstat_entry("/scratch/run/link")
    assert item.path == "/scratch/run/link"
    assert item.name == "link"
    assert item.is_dir is False
    assert stat.S_ISLNK(item.mode)
    assert item.size == 12
    assert item.mtime == 45
    assert calls == [("lstat", "/scratch/run/link")]


def test_stat_entry_still_follows_link_and_is_not_changed():
    backend, calls = _backend()
    item = backend.stat_entry("/scratch/run/link")
    assert item.is_dir is True
    assert stat.S_ISDIR(item.mode)
    assert item.size == 4096
    assert calls == [("stat", "/scratch/run/link")]


def test_lstat_entry_translates_sftp_not_found_to_path_bearing_exception():
    backend, _ = _backend()
    def missing(_path):
        raise FileNotFoundError(errno.ENOENT, "missing remote file")
    backend.ssh.sftp.lstat = missing
    with pytest.raises(FileNotFoundError) as result:
        backend.lstat_entry("/scratch/missing-link")
    assert result.value.filename == "/scratch/missing-link"
    assert result.value.errno == errno.ENOENT


def test_lstat_entry_preserves_root_name_fallback():
    backend, _ = _backend()
    item = backend.lstat_entry("/")
    assert item.name == "/"
    assert item.path == "/"

"""W65 SFTP-014: shipped backends expose the fail-closed lstat entry."""
from __future__ import annotations
import stat
from types import SimpleNamespace
import pytest
from hpc_gui.services.files_base import FilesBackend
from hpc_gui.services.files_mock import MockFilesBackend
from hpc_gui.services.files_ssh import SSHFilesBackend


class _FakeSftp:
    def __init__(self, entry=None, error=None):
        self.entry = entry
        self.error = error
        self.calls = []

    def lstat(self, path):
        self.calls.append(path)
        if self.error is not None:
            raise self.error
        return self.entry


class _FakeSsh:
    def __init__(self, sftp):
        self.sftp = sftp


def test_ssh_lstat_entry_uses_lstat_and_maps_fields():
    entry = SimpleNamespace(st_mode=stat.S_IFLNK | 0o777, st_size=0, st_mtime=1_700_000_000)
    sftp = _FakeSftp(entry=entry)

    result = SSHFilesBackend(_FakeSsh(sftp)).lstat_entry("/case/link")

    assert sftp.calls == ["/case/link"]
    assert result.path == "/case/link"
    assert stat.S_ISLNK(result.mode)
    assert result.is_dir is False


def test_ssh_lstat_entry_propagates_backend_errors():
    sftp = _FakeSftp(error=OSError("permission denied"))

    with pytest.raises(OSError):
        SSHFilesBackend(_FakeSsh(sftp)).lstat_entry("/case/locked")


def test_mock_backend_reports_directories_and_files():
    backend = MockFilesBackend()

    directory = backend.lstat_entry("/arf/scratch/user")
    file_entry = backend.lstat_entry("/arf/scratch/user/example.txt")

    assert directory.is_dir is True and stat.S_ISDIR(directory.mode)
    assert file_entry.is_dir is False and stat.S_ISREG(file_entry.mode)
    assert file_entry.size > 0


def test_mock_backend_rejects_unknown_paths():
    with pytest.raises(FileNotFoundError):
        MockFilesBackend().lstat_entry("/arf/does-not-exist")


def test_base_backend_keeps_lstat_optional():
    with pytest.raises(NotImplementedError):
        FilesBackend.lstat_entry(object(), "/x")


def test_remote_lint_refuses_an_adapter_without_lstat():
    from hpc_gui.plugin_engines.openfoam_lint.remote_case import lint_remote_path

    class BackendWithoutLstat:
        def listdir(self, _path):
            return []

    with pytest.raises(ValueError, match="symbolic links"):
        lint_remote_path("/case", BackendWithoutLstat())

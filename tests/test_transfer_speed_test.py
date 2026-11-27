from __future__ import annotations

from pathlib import Path

import pytest

from hpc_gui.services import transfer_speed_test
from hpc_gui.services.transfer_speed_test import run_transfer_speed_test


class _Files:
    def __init__(self) -> None:
        self.remote: dict[str, bytes] = {}
        self.removed: list[str] = []

    def upload(self, local_path: str, remote_path: str) -> None:
        self.remote[remote_path] = Path(local_path).read_bytes()

    def download(self, remote_path: str, local_path: str) -> None:
        Path(local_path).write_bytes(self.remote[remote_path])

    def remove(self, remote_path: str) -> None:
        self.removed.append(remote_path)
        self.remote.pop(remote_path, None)


@pytest.mark.integration
@pytest.mark.semantic
@pytest.mark.resource
def test_speed_test_round_trip_verifies_and_cleans_up(monkeypatch, tmp_path) -> None:
    def named_temporary_file(**_kwargs):
        return (tmp_path / "speed.bin").open("w+b")

    monkeypatch.setattr(transfer_speed_test.tempfile, "NamedTemporaryFile", named_temporary_file)
    files = _Files()
    result = run_transfer_speed_test(files, remote_dir="/scratch/{user}", size_mib=1)
    assert result["size_mib"] == 1
    assert result["upload_mib_s"] > 0
    assert result["download_mib_s"] > 0
    assert files.removed == [result["remote_path"]]
    assert not files.remote


@pytest.mark.parametrize("failure", ["download", "checksum"])
def test_speed_test_failure_still_cleans_local_and_remote_files(monkeypatch, tmp_path, failure) -> None:
    def named_temporary_file(**_kwargs):
        return (tmp_path / "speed.bin").open("w+b")

    monkeypatch.setattr(transfer_speed_test.tempfile, "NamedTemporaryFile", named_temporary_file)

    class FailingFiles(_Files):
        def download(self, remote_path, local_path):
            if failure == "download":
                raise OSError("disposable download failure")
            super().download(remote_path, local_path)
            Path(local_path).write_bytes(b"different payload")

    files = FailingFiles()
    with pytest.raises((OSError, ValueError)):
        run_transfer_speed_test(files, remote_dir="/scratch/test", size_mib=1)
    assert not files.remote
    assert len(files.removed) == 1
    assert sorted(path.name for path in tmp_path.iterdir()) == []


def test_speed_test_reports_remote_cleanup_failure_and_cleans_local_files(monkeypatch, tmp_path) -> None:
    def named_temporary_file(**_kwargs):
        return (tmp_path / "speed.bin").open("w+b")

    monkeypatch.setattr(transfer_speed_test.tempfile, "NamedTemporaryFile", named_temporary_file)

    class RemovalFailFiles(_Files):
        def remove(self, remote_path):
            self.removed.append(remote_path)
            raise OSError("remote remove failed")

    files = RemovalFailFiles()
    with pytest.raises(RuntimeError, match="remote temporary file cleanup failed"):
        run_transfer_speed_test(files, remote_dir="/scratch/test", size_mib=1)
    assert len(files.removed) == 1
    assert sorted(path.name for path in tmp_path.iterdir()) == []

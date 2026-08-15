from __future__ import annotations

from pathlib import Path

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

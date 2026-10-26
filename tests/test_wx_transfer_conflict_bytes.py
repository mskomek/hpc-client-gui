"""Real backend byte semantics for wx transfer conflict decisions."""

import pytest

from hpc_gui.services.transfer_controller import TransferItem
from hpc_gui.wx_shell import _start_file_transfers
from test_transfer_resume_semantics import (
    PARTIAL,
    REMOTE_FILE,
    SOURCE,
    ftp_backend,
    ssh_backend,
)

pytestmark = pytest.mark.wx


class _Lifecycle:
    def __init__(self):
        self.cleanups = []

    def register_cleanup(self, callback):
        self.cleanups.append(callback)


def _run_decision(files, item, decision):
    controller = _start_file_transfers(
        {"session": {"files": files}, "conflict_policy": "ask"},
        _Lifecycle(),
        [item],
        conflict_resolver=lambda _item: decision,
    )
    assert controller.engine.wait(5)
    return controller


@pytest.mark.parametrize(
    "decision,expected",
    [
        ("overwrite", SOURCE),
        ("resume", PARTIAL + SOURCE[len(PARTIAL) :]),
    ],
)
@pytest.mark.integration
@pytest.mark.semantic
def test_conflict_decision_drives_ftp_upload_bytes(
    tmp_path, decision, expected, disable_optional_transfer_checksums
):
    source = tmp_path / "src.bin"
    source.write_bytes(SOURCE)
    files = ftp_backend({REMOTE_FILE: PARTIAL})
    _run_decision(files, TransferItem("upload", str(source), REMOTE_FILE), decision)
    assert bytes(files.ftp.files[REMOTE_FILE]) == expected
    assert files.ftp.transfer_commands == (["STOR"] if decision == "overwrite" else ["APPE"])


@pytest.mark.parametrize(
    "decision,expected",
    [
        ("overwrite", SOURCE),
        ("resume", PARTIAL + SOURCE[len(PARTIAL) :]),
    ],
)
@pytest.mark.integration
@pytest.mark.semantic
def test_conflict_decision_drives_ssh_upload_bytes(
    tmp_path, decision, expected, disable_optional_transfer_checksums
):
    source = tmp_path / "src.bin"
    source.write_bytes(SOURCE)
    files, sftp = ssh_backend({REMOTE_FILE: PARTIAL})
    _run_decision(files, TransferItem("upload", str(source), REMOTE_FILE), decision)
    assert bytes(sftp.store[REMOTE_FILE]) == expected
    assert sftp.modes(REMOTE_FILE) == (["wb"] if decision == "overwrite" else ["ab"])


@pytest.mark.parametrize(
    "decision,expected",
    [
        ("overwrite", SOURCE),
        ("resume", PARTIAL + SOURCE[len(PARTIAL) :]),
    ],
)
@pytest.mark.integration
@pytest.mark.semantic
def test_conflict_decision_drives_ssh_download_bytes(
    tmp_path, decision, expected, disable_optional_transfer_checksums
):
    local = tmp_path / "dst.bin"
    local.write_bytes(PARTIAL)
    files, sftp = ssh_backend({REMOTE_FILE: SOURCE})
    _run_decision(files, TransferItem("download", REMOTE_FILE, str(local)), decision)
    assert local.read_bytes() == expected
    assert sftp.seeks(REMOTE_FILE) == ([] if decision == "overwrite" else [len(PARTIAL)])


@pytest.mark.parametrize(
    "decision,expected",
    [
        ("overwrite", SOURCE),
        ("resume", PARTIAL + SOURCE[len(PARTIAL) :]),
    ],
)
@pytest.mark.integration
@pytest.mark.semantic
def test_conflict_decision_drives_ftp_download_bytes(
    tmp_path, decision, expected, disable_optional_transfer_checksums
):
    local = tmp_path / "dst.bin"
    local.write_bytes(PARTIAL)
    files = ftp_backend({REMOTE_FILE: SOURCE})
    _run_decision(files, TransferItem("download", REMOTE_FILE, str(local)), decision)
    assert local.read_bytes() == expected
    assert files.ftp.rest_offsets == ([None] if decision == "overwrite" else [len(PARTIAL)])

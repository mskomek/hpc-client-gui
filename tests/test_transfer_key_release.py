"""Transfer path reservations survive active work and release after cancel."""

from threading import Event
from pathlib import Path

from hpc_gui.services.files_mock import MockFilesBackend
from hpc_gui.services.transfer_controller import TransferItem
from hpc_gui.wx_shell_file_transfer import _start_file_transfers


def test_cancel_releases_download_path_for_a_later_queue(tmp_path):
    started = Event()
    release = Event()

    class BlockingFiles(MockFilesBackend):
        def __init__(self):
            super().__init__()
            self.calls = 0

        def download(self, remote, local, progress_cb=None):
            self.calls += 1
            if self.calls == 1:
                Path(local).write_bytes(b"partial")
                started.set()
                assert release.wait(5), "test did not release blocked transfer"
                progress_cb(1, 2)
                return
            super().download(remote, local, progress_cb=progress_cb)

    files = BlockingFiles()
    remote = "/arf/scratch/user/retry.bin"
    files._files[remote] = b"complete payload"
    target = tmp_path / "retry.bin"
    item = TransferItem("download", remote, str(target))
    state = {"session": {"files": files}, "ftp_transfer_type": "binary"}

    active = _start_file_transfers(state, None, [item], conflict_resolver=lambda _: "overwrite")
    assert started.wait(5), "first transfer did not enter its backend"

    duplicate = _start_file_transfers(
        state, None, [TransferItem("download", remote, str(target))],
        conflict_resolver=lambda _: "overwrite",
    )
    assert duplicate.engine.wait(5)
    assert "Another transfer owns" in duplicate.engine.failed[0][1]
    assert files.calls == 1

    active.engine.cancel_all()
    release.set()
    assert active.engine.wait(5)
    assert active.engine.failed[0][1] == "cancelled"

    retry = _start_file_transfers(
        state, None, [TransferItem("download", remote, str(target))],
        conflict_resolver=lambda _: "overwrite",
    )
    assert retry.engine.wait(5)
    assert not retry.engine.failed, retry.engine.failed
    assert files.calls == 2
    assert target.read_bytes() == b"complete payload"

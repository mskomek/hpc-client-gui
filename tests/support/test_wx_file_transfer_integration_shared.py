import pytest
from hpc_gui.services.transfer_controller import TransferItem
from hpc_gui.wx_shell import _start_file_transfers
import time
from threading import Event
class _Files:
    def __init__(self):
        self.calls = []

    def upload(self, source, destination):
        self.calls.append(("upload", source, destination))

    def download(self, source, destination):
        self.calls.append(("download", source, destination))
class _ResumableFiles(_Files):
    def __init__(self, direction):
        super().__init__()
        self.direction = direction
        self.existing = {"/work/item"}

    def exists(self, path):
        return path in self.existing

    def resume_upload(self, source, destination):
        assert self.direction == "upload"
        self.calls.append(("resume_upload", source, destination))

    def resume_download(self, source, destination):
        assert self.direction == "download"
        self.calls.append(("resume_download", source, destination))
class _Lifecycle:
    def __init__(self):
        self.cleanups = []

    def register_cleanup(self, callback):
        self.cleanups.append(callback)
class _FailingFiles(_Files):
    def upload(self, source, destination):
        super().upload(source, destination)
        raise OSError("transfer failed")
class _BlockingFiles(_Files):
    def __init__(self):
        super().__init__()
        self.started = Event()
        self.release = Event()

    def upload(self, source, destination):
        super().upload(source, destination)
        self.started.set()
        self.release.wait(2)
class _ConflictFiles(_Files):
    def __init__(self):
        super().__init__()
        self.existing = {"/work/a.txt"}

    def exists(self, path):
        return path in self.existing
def _run_conflict(policy, resolver=None):
    files = _ConflictFiles()
    state = {"session": {"files": files}, "conflict_policy": policy}
    controller = _start_file_transfers(
        state,
        _Lifecycle(),
        [TransferItem("upload", "a.txt", "/work/a.txt")],
        conflict_resolver=resolver,
    )
    assert controller.engine.wait(2)
    return files.calls
from test_transfer_resume_semantics import (  # noqa: E402
    PARTIAL,
    REMOTE_FILE,
    SOURCE,
    ftp_backend,
    ssh_backend,
)
def _run_decision(files, item, decision):
    controller = _start_file_transfers(
        {"session": {"files": files}, "conflict_policy": "ask"},
        _Lifecycle(),
        [item],
        conflict_resolver=lambda _item: decision,
    )
    assert controller.engine.wait(5)
    return controller

__all__ = [
    'pytest',
    'TransferItem',
    '_start_file_transfers',
    'time',
    'Event',
    '_Files',
    '_ResumableFiles',
    '_Lifecycle',
    '_FailingFiles',
    '_BlockingFiles',
    '_ConflictFiles',
    '_run_conflict',
    'PARTIAL',
    'REMOTE_FILE',
    'SOURCE',
    'ftp_backend',
    'ssh_backend',
    '_run_decision',
]

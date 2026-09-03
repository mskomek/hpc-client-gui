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


def test_file_context_transfer_uses_transfer_session_boundary():
    files = _Files()
    lifecycle = _Lifecycle()
    state = {"session": {"files": files}}
    controller = _start_file_transfers(state, lifecycle, [TransferItem("upload", "iş sonuç.txt", "/work/iş sonuç.txt")])
    assert controller.engine.wait(2)
    assert files.calls == [("upload", "iş sonuç.txt", "/work/iş sonuç.txt")]
    assert lifecycle.cleanups


def test_wx_file_transfer_session_removed_after_success():
    files = _Files()
    state = {"session": {"files": files}}
    controller = _start_file_transfers(state, _Lifecycle(), [TransferItem("upload", "a.txt", "/a.txt")])
    assert controller.engine.wait(2)
    deadline = time.monotonic() + 1
    while time.monotonic() < deadline and state.get("transfer_sessions"):
        time.sleep(0.01)
    assert state["transfer_sessions"] == set()


def test_wx_file_transfer_session_removed_after_failure():
    state = {"session": {"files": _FailingFiles()}}
    controller = _start_file_transfers(state, _Lifecycle(), [TransferItem("upload", "a.txt", "/a.txt")])
    assert controller.engine.wait(2)
    deadline = time.monotonic() + 1
    while time.monotonic() < deadline and state.get("transfer_sessions"):
        time.sleep(0.01)
    assert state["transfer_sessions"] == set()


def test_wx_file_transfer_session_removed_after_cancel():
    files = _BlockingFiles()
    state = {"session": {"files": files}}
    controller = _start_file_transfers(state, _Lifecycle(), [TransferItem("upload", "a.txt", "/a.txt")])
    assert files.started.wait(2)
    controller.cancel()
    files.release.set()
    assert controller.engine.wait(2)
    deadline = time.monotonic() + 1
    while time.monotonic() < deadline and state.get("transfer_sessions"):
        time.sleep(0.01)
    assert state["transfer_sessions"] == set()

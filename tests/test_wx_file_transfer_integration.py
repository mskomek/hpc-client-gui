from hpc_gui.services.transfer_controller import TransferItem
from hpc_gui.wx_shell import _start_file_transfers


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


def test_file_context_transfer_uses_transfer_session_boundary():
    files = _Files()
    lifecycle = _Lifecycle()
    state = {"session": {"files": files}}
    controller = _start_file_transfers(state, lifecycle, [TransferItem("upload", "iş sonuç.txt", "/work/iş sonuç.txt")])
    assert controller.engine.wait(2)
    assert files.calls == [("upload", "iş sonuç.txt", "/work/iş sonuç.txt")]
    assert lifecycle.cleanups

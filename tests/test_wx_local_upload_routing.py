from __future__ import annotations

from pathlib import Path
from threading import Event
from types import SimpleNamespace

import pytest

from hpc_gui import wx_shell_files
from hpc_gui.services.transfer_controller import TransferItem
from hpc_gui.wx_shell_file_transfer import _run_file_view_item, _start_file_transfers


class _Files:
    def __init__(self):
        self.calls = []
        self.remote = {}

    def mkdir(self, destination):
        self.calls.append(("mkdir", destination))
        self.remote.setdefault(destination, None)

    def upload(self, source, destination):
        self.calls.append(("upload", source, destination))
        self.remote[destination] = Path(source).read_bytes()


class _Notebook:
    def GetSelection(self):
        return 1


def _callbacks(monkeypatch, state):
    monkeypatch.setattr(
        wx_shell_files,
        "_get_editor_manager",
        lambda *_args, **_kwargs: object(),
    )
    return wx_shell_files._local_files_callbacks(state, object(), None)


@pytest.mark.unit
def test_upload_callback_targets_active_remote_tab_and_builds_recursive_plan(
    monkeypatch, tmp_path: Path
):
    selected_file = tmp_path / "top.txt"
    selected_file.write_text("top", encoding="utf-8")
    folder = tmp_path / "Solver"
    nested = folder / "inputs"
    nested.mkdir(parents=True)
    (folder / "run.slurm").write_text("run", encoding="utf-8")
    (nested / "mesh.dat").write_text("mesh", encoding="utf-8")
    (folder / "empty").mkdir()

    panel = SimpleNamespace(
        _wx_remote_tabs=[{"path": "/ignored"}, {"path": "/arf/scratch/mkomek"}],
        _wx_remote_notebook=_Notebook(),
    )
    state = {"session": {"files": _Files()}, "_embedded_remote_files_panel": panel}
    submitted = []
    ready = Event()

    def capture(_state, _lifecycle, items, **kwargs):
        submitted.append((items, kwargs))
        ready.set()

    monkeypatch.setattr(wx_shell_files, "_start_file_transfers", capture)
    _callbacks(monkeypatch, state)["upload"]((str(selected_file), str(folder)))
    assert ready.wait(2)

    items, kwargs = submitted[0]
    backend = kwargs["files_backend"]
    assert backend is state["session"]["files"]
    assert [(item.op, item.src, item.dst) for item in items] == [
        ("upload", str(selected_file.resolve()), "/arf/scratch/mkomek/top.txt"),
        ("mkdir_remote", "", "/arf/scratch/mkomek/Solver"),
        ("mkdir_remote", "", "/arf/scratch/mkomek/Solver/empty"),
        ("mkdir_remote", "", "/arf/scratch/mkomek/Solver/inputs"),
        ("upload", str(folder / "run.slurm"), "/arf/scratch/mkomek/Solver/run.slurm"),
        ("upload", str(nested / "mesh.dat"), "/arf/scratch/mkomek/Solver/inputs/mesh.dat"),
    ]
    controller = _start_file_transfers(state, None, items, files_backend=backend)
    assert controller.engine.wait(2)
    assert not controller.engine.failed
    assert backend.remote == {
        "/arf/scratch/mkomek/Solver": None,
        "/arf/scratch/mkomek/Solver/empty": None,
        "/arf/scratch/mkomek/Solver/inputs": None,
        "/arf/scratch/mkomek/top.txt": b"top",
        "/arf/scratch/mkomek/Solver/run.slurm": b"run",
        "/arf/scratch/mkomek/Solver/inputs/mesh.dat": b"mesh",
    }


@pytest.mark.unit
def test_upload_callback_uses_remote_model_path_when_tab_state_is_unavailable(
    monkeypatch, tmp_path: Path
):
    source = tmp_path / "one.txt"
    source.write_text("one", encoding="utf-8")
    panel = SimpleNamespace(_wx_remote_model=SimpleNamespace(current_path="relative/path"))
    state = {"session": {"files": _Files()}, "_embedded_remote_files_panel": panel}
    submitted = []
    ready = Event()
    monkeypatch.setattr(
        wx_shell_files,
        "_start_file_transfers",
        lambda _state, _lifecycle, items, **_kwargs: (submitted.extend(items), ready.set()),
    )
    _callbacks(monkeypatch, state)["upload"]((str(source),))
    assert ready.wait(2)
    assert submitted == [
        TransferItem("upload", str(source.resolve()), "/relative/path/one.txt")
    ]


@pytest.mark.unit
def test_upload_fails_visibly_instead_of_defaulting_to_remote_root(monkeypatch, tmp_path):
    source = tmp_path / "one.txt"
    source.write_text("one", encoding="utf-8")
    state = {"session": {"files": _Files()}}
    callbacks = _callbacks(monkeypatch, state)
    wx = pytest.importorskip("wx")
    messages = []
    monkeypatch.setattr(wx, "MessageBox", lambda message, *_args: messages.append(message))
    callbacks["upload"]((str(source),))
    assert messages and "active remote directory is unavailable" in messages[0]


@pytest.mark.unit
@pytest.mark.parametrize(
    "operation, expected",
    [
        ("upload", "Upload failed.*Permission denied"),
        ("mkdir_remote", "Remote directory creation failed.*Permission denied"),
    ],
)
def test_backend_failures_keep_operation_destination_and_real_reason(operation, expected):
    class DeniedFiles:
        def upload(self, _source, _destination):
            raise PermissionError("Permission denied")

        def mkdir(self, _destination):
            raise PermissionError("Permission denied")

    item = TransferItem(operation, "local.bin", "/work/Solver/local.bin")
    with pytest.raises(RuntimeError, match=expected) as failure:
        _run_file_view_item(DeniedFiles(), item, lambda *_args: None)
    assert "/work/Solver" in str(failure.value)


@pytest.mark.integration
def test_recursive_upload_items_create_directories_and_retry_keeps_destination(tmp_path):
    source = tmp_path / "source.bin"
    source.write_bytes(b"payload")

    class RetryFiles:
        def __init__(self):
            self.calls = []
            self.failed_once = False

        def mkdir(self, destination):
            self.calls.append(("mkdir", destination))

        def upload(self, local_path, destination):
            self.calls.append(("upload", local_path, destination))
            if not self.failed_once:
                self.failed_once = True
                raise OSError("Connection reset")

    files = RetryFiles()
    destination = "/arf/scratch/mkomek/Solver/source.bin"
    controller = _start_file_transfers(
        {"session": {"files": files}},
        None,
        [
            TransferItem("mkdir_remote", "", "/arf/scratch/mkomek/Solver"),
            TransferItem("upload", str(source), destination),
        ],
    )
    assert controller.engine.wait(2)
    assert controller.engine.failed[0][0].dst == destination
    assert "Connection reset" in controller.engine.failed[0][1]
    assert controller.engine.retry_failed() == 1
    controller.engine.start()
    assert controller.engine.wait(2)
    assert not controller.engine.failed
    assert files.calls == [
        ("mkdir", "/arf/scratch/mkomek/Solver"),
        ("upload", str(source), destination),
        ("upload", str(source), destination),
    ]


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.integration
def test_failed_row_exposes_backend_error_and_retry_reuses_target(tmp_path):
    wx = pytest.importorskip("wx")
    from hpc_gui.wx_transfer_workspace import build_transfers_panel

    app = wx.App.Get() or wx.App(False)
    frame = wx.Frame(None)
    transfers = build_transfers_panel(frame)
    source = tmp_path / "retry.txt"
    source.write_text("payload", encoding="utf-8")

    class TransientFiles(_Files):
        def __init__(self):
            super().__init__()
            self.failed_once = False

        def upload(self, local_path, destination):
            self.calls.append(("upload", local_path, destination))
            if not self.failed_once:
                self.failed_once = True
                raise PermissionError("Permission denied by test server")
            self.remote[destination] = Path(local_path).read_bytes()

    files = TransientFiles()
    state = {
        "session": {"files": files},
        "embedded_transfers_panel": transfers,
    }
    target = "/arf/scratch/mkomek/Solver/retry.txt"
    controller = _start_file_transfers(
        state,
        None,
        [TransferItem("upload", str(source), target)],
    )
    controls = transfers._wx_transfer_controls

    def pump_until(predicate, timeout=3):
        import time

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            app.ProcessPendingEvents()
            if predicate():
                return True
            wx.MilliSleep(5)
        app.ProcessPendingEvents()
        return bool(predicate())

    try:
        assert pump_until(lambda: controller.engine.wait(0) and controls["failed"].GetItemCount() == 1)
        row = controls["failed"].GetItemText(0, 6)
        assert "Permission denied by test server" in row
        retry = controls["retry_failed"]
        assert retry.IsEnabled()
        retry.ProcessEvent(wx.CommandEvent(wx.wxEVT_BUTTON, retry.GetId()))
        assert pump_until(lambda: controller.engine.wait(0) and controls["completed"].GetItemCount() == 1)
        assert files.calls == [("upload", str(source), target), ("upload", str(source), target)]
        assert files.remote[target] == b"payload"
    finally:
        frame.Destroy()
        app.ProcessPendingEvents()
        wx.YieldIfNeeded()
        app.ProcessPendingEvents()
        app.Destroy()

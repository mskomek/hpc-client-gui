"""GUI-FILE-003 FILE transfer item stress group."""

from __future__ import annotations

import threading

import time

import pytest

wx = pytest.importorskip("wx")

from hpc_gui.core.i18n import load_language

from support.wx_file003_stress import METRICS, _record

def _settle(app, rounds: int = 6) -> None:
    for _ in range(rounds):
        app.ProcessPendingEvents()
        # wx frees closed frames during idle processing, so a loop that only
        # pumps pending events keeps them in GetTopLevelWindows() forever.
        wx.SafeYield()
        wx.MilliSleep(2)
    app.ProcessPendingEvents()
    wx.SafeYield()

@pytest.fixture(scope="module")
def wx_app():
    load_language("en")
    app = wx.App.Get()
    owns_app = app is None
    if owns_app:
        app = wx.App.Get()
        if app is None:
            app = wx.App(False)
    yield app
    _destroy_windows(app)
    if owns_app:
        app.Destroy()

@pytest.fixture(autouse=True)
def _cleanup_windows_after_test(wx_app):
    load_language("en")
    baseline = {id(window) for window in wx.GetTopLevelWindows()}
    yield
    _destroy_windows(wx_app, baseline)

def _destroy_windows(app, baseline=None):
    baseline = baseline or set()
    for window in wx.GetTopLevelWindows():
        if window and id(window) not in baseline:
            window.Destroy()
    _settle(app)

class _Lifecycle:
    def __init__(self):
        self.cleanups = []

    def register_cleanup(self, callback):
        self.cleanups.append(callback)

class _AccountingFiles:
    """Records every backend-started transfer id exactly as it happens."""

    def __init__(self, existing=(), failing=()):
        self.lock = threading.Lock()
        self.existing = set(existing)
        self.failing = set(failing)
        self.started = []
        self.methods = []

    def exists(self, path):
        return path in self.existing

    def _run(self, method, identity):
        with self.lock:
            self.started.append(identity)
            self.methods.append(method)
        if identity in self.failing:
            raise OSError("transfer failed for " + identity)

    def upload(self, source, destination):
        self._run("upload", destination)

    def download(self, source, destination):
        self._run("download", destination)

    def resume_upload(self, source, destination):
        self._run("resume_upload", destination)

    def resume_download(self, source, destination):
        self._run("resume_download", destination)

@pytest.mark.integration
@pytest.mark.semantic
@pytest.mark.regression
@pytest.mark.concurrency
@pytest.mark.resource
def test_stress_h_file_transfer_items(wx_app, tmp_path):
    from hpc_gui.services.transfer_controller import TransferItem
    from hpc_gui.wx_shell import _start_file_transfers

    submitted = []
    completed = []
    failed = []
    pending = []
    all_started = []
    session_state = {}

    for batch_index in range(10):
        destinations = ["/remote/b%d-i%d.bin" % (batch_index, item) for item in range(10)]
        conflicting = {destinations[position] for position in (1, 2, 3, 4)}
        failing = {destinations[5]} if batch_index % 2 == 0 else set()
        files = _AccountingFiles(existing=conflicting, failing=failing)
        session_state["session"] = {"files": files}

        (tmp_path / "src.bin").write_text("payload", encoding="utf-8")
        plain_download = tmp_path / ("down-%d-plain.bin" % batch_index)
        resumed_download = tmp_path / ("down-%d-resume.bin" % batch_index)
        resumed_download.write_bytes(b"partial")  # a real local-side conflict

        items = []
        for position, destination in enumerate(destinations):
            if position == 7:
                items.append(TransferItem("download", "/remote/src.bin", str(plain_download)))
            elif position == 8:
                items.append(TransferItem("download", "/remote/src.bin", str(resumed_download)))
            else:
                items.append(TransferItem("upload", str(tmp_path / "src.bin"), destination))
        submitted.extend(id(item) for item in items)

        decisions = {
            destinations[1]: "overwrite",
            destinations[2]: "resume",
            destinations[3]: "skip",
            destinations[4]: ("rename", destinations[4] + ".renamed"),
            str(resumed_download): "resume",
        }
        cancel_at = destinations[6] if batch_index == 9 else None
        if cancel_at:
            files.existing.add(cancel_at)

        def resolver(item, _decisions=decisions, _cancel=cancel_at):
            if _cancel and item.dst == _cancel:
                return "cancel"
            return _decisions.get(item.dst, "overwrite")

        controller = _start_file_transfers(
            session_state,
            _Lifecycle(),
            items,
            conflict_resolver=resolver,
        )
        assert controller.engine.wait(10)
        completed.extend(id(item) for item in controller.engine.completed)
        failed.extend(id(item) for item, _error in controller.engine.failed)
        pending.extend(id(item) for item in controller.engine.pending)
        all_started.extend(files.started)
        # The resume decision must reach the direction-specific backend method.
        assert "resume_upload" in files.methods, files.methods
        if not cancel_at:
            # The cancel batch stops before the download items by design.
            assert "resume_download" in files.methods, files.methods

    executed = len(submitted)
    terminal = set(completed) | set(failed) | set(pending)
    METRICS["lost_transfers"] += len(set(submitted) - terminal)
    METRICS["duplicate_transfers"] += len(all_started) - len(set(all_started))
    if session_state.get("transfer_sessions"):
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline and session_state["transfer_sessions"]:
            _settle(wx_app, 2)
        METRICS["leaked_transfer_sessions"] += len(session_state["transfer_sessions"])

    _record("FILE transfer items", executed, 100)
    assert len(completed) + len(failed) + len(pending) == 100
    assert len(failed) >= 5 and len(completed) >= 80 and len(pending) >= 1
    assert METRICS["lost_transfers"] == 0
    assert METRICS["duplicate_transfers"] == 0
    assert METRICS["leaked_transfer_sessions"] == 0

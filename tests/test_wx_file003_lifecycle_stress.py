from __future__ import annotations

# Fixture parameters intentionally shadow the imported fixture declaration.
# ruff: noqa: F811

from pathlib import Path

import pytest

pytestmark = [pytest.mark.wx]

from support.wx_file003_stress_support import (
    BlockingTransferFiles as _BlockingTransferFiles, DestroyedControlProbe,
    EXECUTED, Lifecycle as _Lifecycle, METRICS, _activate, _close_first_tab, _enter_path,
    _file_browser_windows, _key, _local_frame, _pump,
    _record, _remote_frame, _rows, _select_only, _settle,
    threading, time, wx,
)
from support.wx_file003_stress_support import wx_app, _cleanup_windows_after_test  # noqa: F401
from hpc_gui.wx_local_files import LocalBrowserModel
from hpc_gui.wx_remote_files import RemoteEntry
from mock_hpc_files import MockRemoteFilesBackend

@pytest.mark.gui
@pytest.mark.semantic
@pytest.mark.regression
@pytest.mark.resource
@pytest.mark.slow
def test_stress_f_browser_open_close(wx_app, tmp_path):
    (tmp_path / "sample.txt").write_text("x", encoding="utf-8")
    baseline = {id(window) for window in _file_browser_windows()}
    backend = MockRemoteFilesBackend()
    probe = DestroyedControlProbe()

    executed = 0
    for index in range(50):
        if index % 2 == 0:
            frame = _local_frame(wx_app, tmp_path)
            listing = frame._wx_local_controls["listing"]
            _pump(wx_app, lambda: "sample.txt" in _rows(listing))
        else:
            frame = _remote_frame(wx_app, backend)
            listing = frame._wx_remote_controls["listing"]
            _pump(wx_app, lambda: listing.GetItemCount() >= 1)
        probe.watch(listing)
        probe.mark_destroyed()
        frame.Close(True)
        _settle(wx_app, 8)
        executed += 1
        leaked = [window for window in _file_browser_windows() if id(window) not in baseline]
        if leaked:
            METRICS["leaked_wx_windows"] += len(leaked)
            for window in leaked:
                window.Destroy()
            _settle(wx_app)

    _record("browser open/close", executed, 50)
    assert METRICS["leaked_wx_windows"] == 0
    assert METRICS["destroyed_control_callbacks"] == 0

@pytest.mark.gui
@pytest.mark.semantic
@pytest.mark.regression
@pytest.mark.concurrency
@pytest.mark.resource
@pytest.mark.slow
def test_stress_g_blocked_close_in_flight(wx_app, tmp_path, monkeypatch):
    from hpc_gui.services.transfer_controller import TransferItem
    from hpc_gui.wx_local_files import LocalEntry
    from hpc_gui.wx_shell import _start_file_transfers

    dialogs = []

    def record_message_box(message, caption="", style=0, *args, **kwargs):
        # Only an error box is evidence of a stale completion; the delete
        # confirmation is the production contract.
        if style & wx.ICON_ERROR:
            dialogs.append((message, caption, style))
        return wx.YES

    monkeypatch.setattr(wx, "MessageBox", record_message_box)
    baseline_windows = {id(window) for window in _file_browser_windows()}
    baseline_threads = set(threading.enumerate())
    probe = DestroyedControlProbe()
    executed = 0

    # --- remote listing in flight, frame closed (5) ---
    for index in range(5):
        release = threading.Event()

        def loader(path, _release=release):
            if path == "/slow":
                _release.wait(3)
            return (RemoteEntry("/slow", is_dir=True), RemoteEntry("/work/a.txt", is_dir=False))

        backend = MockRemoteFilesBackend()
        frame = _remote_frame(wx_app, backend, loader=loader)
        listing = frame._wx_remote_controls["listing"]
        probe.watch(listing)
        _enter_path(frame, "/slow")
        _settle(wx_app, 2)
        probe.mark_destroyed()
        frame.Close(True)
        _settle(wx_app, 4)
        release.set()
        _settle(wx_app, 10)
        executed += 1

    # --- local listing in flight, frame closed (5) ---
    for index in range(5):
        release = threading.Event()
        slow = tmp_path / ("slow-%d" % index)
        slow.mkdir()

        def entries(self, path=None, _release=release, _slow=slow):
            if Path(path or self.current_path).resolve() == _slow.resolve():
                _release.wait(3)
                return (LocalEntry(_slow / "late.txt", False, 0),)
            return (LocalEntry(_slow, True, 0),)

        monkeypatch.setattr(LocalBrowserModel, "list_entries", entries)
        frame = _local_frame(wx_app, tmp_path)
        listing = frame._wx_local_controls["listing"]
        probe.watch(listing)
        _pump(wx_app, lambda: slow.name in _rows(listing))
        _activate(listing, _rows(listing).index(slow.name))
        _settle(wx_app, 2)
        probe.mark_destroyed()
        frame.Close(True)
        _settle(wx_app, 4)
        release.set()
        _settle(wx_app, 10)
        executed += 1
    monkeypatch.undo()
    monkeypatch.setattr(wx, "MessageBox", record_message_box)

    # --- remote mutation in flight, active tab closed (5) ---
    for index in range(5):
        release = threading.Event()
        backend = MockRemoteFilesBackend()
        backend.entries["/scratch"] = True
        original_operation = backend.operation

        def blocking_operation(*args, _release=release, _original=original_operation, **kwargs):
            _release.wait(3)
            return _original(*args, **kwargs)

        backend.operation = blocking_operation
        frame = _remote_frame(wx_app, backend)
        frame._wx_remote_run_action("new_tab", ("/scratch",), "/scratch")
        _pump(wx_app, lambda: frame._wx_remote_notebook.GetPageCount() == 2)
        listing = frame._wx_remote_controls["listing"]
        probe.watch(listing)
        frame._wx_remote_run_action("delete", ("/scratch/gone.txt",), "/scratch")
        _settle(wx_app, 2)
        _close_first_tab(frame._wx_remote_notebook)
        _settle(wx_app, 4)
        release.set()
        _settle(wx_app, 10)
        frame.Destroy()
        _settle(wx_app, 4)
        executed += 1

    # --- local mutation in flight, frame closed (5) ---
    for index in range(5):
        release = threading.Event()
        target = tmp_path / ("mutate-%d.txt" % index)
        target.write_text("x", encoding="utf-8")

        def blocking_delete(self, paths, origin_dir, _release=release):
            _release.wait(3)
            return ()

        monkeypatch.setattr(LocalBrowserModel, "delete_at", blocking_delete)
        frame = _local_frame(wx_app, tmp_path)
        listing = frame._wx_local_controls["listing"]
        probe.watch(listing)
        _pump(wx_app, lambda: target.name in _rows(listing))
        _select_only(listing, _rows(listing).index(target.name))
        _key(listing, wx.WXK_DELETE)
        _settle(wx_app, 2)
        probe.mark_destroyed()
        frame.Close(True)
        _settle(wx_app, 4)
        release.set()
        _settle(wx_app, 10)
        target.unlink(missing_ok=True)
        executed += 1

    # --- transfer in flight, transfer window closed (5) ---
    for index in range(5):
        parent = wx.Frame(None)
        files = _BlockingTransferFiles()
        state = {"session": {"files": files}}
        controller = _start_file_transfers(
            state,
            _Lifecycle(),
            [TransferItem("upload", "a.txt", "/blocked-%d.txt" % index)],
            files_backend=files,
            parent=parent,
        )
        assert files.started.wait(3)
        window = [w for w in wx.GetTopLevelWindows() if hasattr(w, "_wx_transfer_controls")][-1]
        window.Close(True)
        _settle(wx_app, 4)
        files.release.set()
        assert controller.engine.wait(3)
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline and state.get("transfer_sessions"):
            _settle(wx_app, 2)
        if state.get("transfer_sessions"):
            METRICS["leaked_transfer_sessions"] += len(state["transfer_sessions"])
        parent.Destroy()
        _settle(wx_app, 4)
        executed += 1

    for window in _file_browser_windows():
        if id(window) in baseline_windows:
            continue
        METRICS["leaked_wx_windows"] += 1
        window.Destroy()
    _settle(wx_app, 6)

    deadline = time.monotonic() + 3
    while time.monotonic() < deadline and (set(threading.enumerate()) - baseline_threads):
        _settle(wx_app, 4)
    METRICS["leaked_file_workers"] += len(set(threading.enumerate()) - baseline_threads)

    _record("blocked close-in-flight", executed, 25)
    assert not dialogs, dialogs[:2]
    assert METRICS["destroyed_control_callbacks"] == 0
    assert METRICS["leaked_wx_windows"] == 0
    assert METRICS["leaked_transfer_sessions"] == 0
    assert METRICS["leaked_file_workers"] == 0

@pytest.mark.reporting
@pytest.mark.semantic
def test_lifecycle_stress_metrics():
    assert all(name in EXECUTED for name in ("browser open/close", "blocked close-in-flight"))
    for name in ("leaked_wx_windows", "destroyed_control_callbacks", "leaked_transfer_sessions", "leaked_file_workers"):
        assert METRICS[name] == 0, f"{name} = {METRICS[name]}"

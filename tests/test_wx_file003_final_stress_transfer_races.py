"""GUI-FILE-003 in-flight transfer and close-race stress groups."""

from __future__ import annotations

import threading

import time

from pathlib import Path

import pytest

wx = pytest.importorskip("wx")

from hpc_gui.core.i18n import load_language

from hpc_gui.wx_local_files import LocalBrowserModel, show_local_files

from hpc_gui.wx_remote_files import RemoteEntry, WxRemoteDirectoryModel

from hpc_gui.wx_remote_files_view import show_remote_files

from mock_hpc_files import MockRemoteFilesBackend

from support.wx_file003_stress import METRICS, _record

def _pump(app, predicate, timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.ProcessPendingEvents()
        if predicate():
            return
        wx.MilliSleep(2)
    app.ProcessPendingEvents()
    assert predicate()

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

def _local_frame(app, path):
    show_local_files(path=path)
    frame = [w for w in wx.GetTopLevelWindows() if hasattr(w, "_wx_local_controls")][-1]
    _pump(app, lambda: frame._wx_local_controls["listing"].GetItemCount() >= 0)
    return frame

def _remote_frame(app, backend, path="/work", loader=None):
    show_remote_files(
        model=WxRemoteDirectoryModel(path),
        loader=loader or backend.iterdir_entries,
        operation=backend.operation,
    )
    frame = [w for w in wx.GetTopLevelWindows() if hasattr(w, "_wx_remote_controls")][-1]
    _pump(app, lambda: frame._wx_remote_controls["listing"].GetItemCount() >= 1)
    return frame

class DestroyedControlProbe:
    """Counts production writes attempted against an already-destroyed control.

    wx raises only sometimes and production wraps those writes in defensive
    ``except RuntimeError`` blocks, so a lifecycle defect would otherwise be
    invisible.  Patching the control's own methods records the attempt.
    """

    METHODS = ("DeleteAllItems", "InsertItem", "SetItem", "Enable", "Select")

    def __init__(self):
        self._armed = []

    def watch(self, control) -> None:
        marker = {"destroyed": False}
        for name in self.METHODS:
            original = getattr(control, name, None)
            if not callable(original):
                continue

            def probe(*args, _original=original, _marker=marker, **kwargs):
                if _marker["destroyed"]:
                    METRICS["destroyed_control_callbacks"] += 1
                    return None
                return _original(*args, **kwargs)

            setattr(control, name, probe)
        self._armed.append(marker)

    def mark_destroyed(self) -> None:
        for marker in self._armed:
            marker["destroyed"] = True

def _key(listing, code, *, ctrl=False, shift=False):
    event = wx.KeyEvent(wx.wxEVT_KEY_DOWN)
    event.SetKeyCode(code)
    event.SetControlDown(ctrl)
    event.SetShiftDown(shift)
    listing.ProcessEvent(event)

def _select_only(listing, *rows):
    for index in range(listing.GetItemCount()):
        listing.Select(index, False)
    for row in rows:
        listing.Select(row)

def _rows(listing):
    return [listing.GetItemText(index) for index in range(listing.GetItemCount())]

def _activate(control, row):
    event = wx.ListEvent(wx.wxEVT_LIST_ITEM_ACTIVATED, control.GetId())
    event.SetIndex(row)
    control.ProcessEvent(event)

def _enter_path(frame, value):
    control = frame._wx_remote_controls["path"]
    control.SetValue(value)
    control.ProcessEvent(wx.CommandEvent(wx.wxEVT_TEXT_ENTER, control.GetId()))

def _file_browser_windows():
    return [
        window
        for window in wx.GetTopLevelWindows()
        if window
        and not window.IsBeingDeleted()
        and (hasattr(window, "_wx_local_controls") or hasattr(window, "_wx_remote_controls") or hasattr(window, "_wx_transfer_controls"))
    ]

class _BlockingTransferFiles:
    def __init__(self):
        self.started = threading.Event()
        self.release = threading.Event()
        self.calls = []

    def upload(self, source, destination):
        self.calls.append(("upload", source, destination))
        self.started.set()
        self.release.wait(3)

    def download(self, source, destination):
        self.calls.append(("download", source, destination))
        self.started.set()
        self.release.wait(3)

class _Lifecycle:
    def __init__(self):
        self.cleanups = []

    def register_cleanup(self, callback):
        self.cleanups.append(callback)

def _close_first_tab(notebook):
    """Close tab 0 the way a user does: notebook context menu -> Close."""
    original_hit, original_popup = notebook.HitTest, notebook.PopupMenu
    notebook.HitTest = lambda point: (0, 0)

    def capture(menu):
        for item in menu.GetMenuItems():
            if item.GetItemLabelText() == "Close":
                notebook.ProcessEvent(wx.CommandEvent(wx.wxEVT_MENU, item.GetId()))
                break

    notebook.PopupMenu = capture
    try:
        event = wx.ContextMenuEvent(wx.wxEVT_CONTEXT_MENU, notebook.GetId())
        event.SetPosition(notebook.ClientToScreen(wx.Point(5, 5)))
        notebook.ProcessEvent(event)
    finally:
        notebook.PopupMenu = original_popup
        notebook.HitTest = original_hit

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

"""GUI-FILE-003 navigation-race and window-lifecycle stress groups."""

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

@pytest.mark.gui
@pytest.mark.semantic
@pytest.mark.regression
@pytest.mark.concurrency
@pytest.mark.slow
def test_stress_e_navigate_completion_races(wx_app, tmp_path, monkeypatch):
    dialogs = []
    monkeypatch.setattr(wx, "MessageBox", lambda *a, **k: dialogs.append(a) or wx.YES)

    # ---------------- remote ----------------
    gate = {"release": threading.Event(), "fail": False, "stale": "STALE-0.txt"}

    def remote_loader(path):
        if path == "/slow":
            gate["release"].wait(3)
            if gate["fail"]:
                raise OSError("late remote failure")
            return (RemoteEntry("/slow/" + gate["stale"], is_dir=False),)
        if path == "/fast":
            return (RemoteEntry("/fast/FAST_ONLY.txt", is_dir=False),)
        return (RemoteEntry("/slow", is_dir=True), RemoteEntry("/fast", is_dir=True))

    backend = MockRemoteFilesBackend()
    frame = _remote_frame(wx_app, backend, path="/", loader=remote_loader)
    _pump(wx_app, lambda: "slow" in _rows(frame._wx_remote_controls["listing"]))

    executed = 0
    for index in range(100):
        gate["release"].clear()
        gate["fail"] = index % 5 == 0
        gate["stale"] = "STALE-%d.txt" % index
        listing = frame._wx_remote_controls["listing"]
        _pump(wx_app, lambda: "slow" in _rows(frame._wx_remote_controls["listing"]))
        _activate(listing, _rows(listing).index("slow"))  # request A, blocked
        _settle(wx_app, 2)
        _enter_path(frame, "/fast")  # navigate to B
        _pump(wx_app, lambda: "FAST_ONLY.txt" in _rows(frame._wx_remote_controls["listing"]))
        gate["release"].set()  # A completes late
        _settle(wx_app, 10)
        rows = set(_rows(frame._wx_remote_controls["listing"]))
        if gate["stale"] in rows:
            METRICS["stale_ui_overwrites"] += 1
        if rows != {"..", "FAST_ONLY.txt"}:
            METRICS["wrong_targets"] += 1
        _enter_path(frame, "/")
        _pump(wx_app, lambda: "slow" in _rows(frame._wx_remote_controls["listing"]))
        executed += 1
    assert not dialogs, dialogs[:2]

    # ---------------- local ----------------
    from hpc_gui.wx_local_files import LocalEntry

    slow_dir = tmp_path / "slow"
    fast_dir = tmp_path / "fast"
    slow_dir.mkdir()
    fast_dir.mkdir()
    local_gate = {"release": threading.Event(), "fail": False, "stale": "local-stale-0.txt"}

    def local_entries(self, path=None):
        target = Path(path or self.current_path).resolve()
        if target == slow_dir.resolve():
            local_gate["release"].wait(3)
            if local_gate["fail"]:
                raise OSError("late local failure")
            return (LocalEntry(slow_dir / local_gate["stale"], False, 0),)
        if target == fast_dir.resolve():
            # Keep both directories reachable so the next race can start here
            # without relying on a parent-navigation gesture.
            return (
                LocalEntry(fast_dir / "FAST_LOCAL.txt", False, 0),
                LocalEntry(slow_dir, True, 0),
                LocalEntry(fast_dir, True, 0),
            )
        return (LocalEntry(slow_dir, True, 0), LocalEntry(fast_dir, True, 0))

    monkeypatch.setattr(LocalBrowserModel, "list_entries", local_entries)
    local_frame = _local_frame(wx_app, tmp_path)
    _pump(wx_app, lambda: "slow" in _rows(local_frame._wx_local_controls["listing"]))

    for index in range(100):
        local_gate["release"].clear()
        local_gate["fail"] = index % 5 == 0
        local_gate["stale"] = "local-stale-%d.txt" % index
        control = local_frame._wx_local_controls["listing"]
        _pump(wx_app, lambda: "slow" in _rows(local_frame._wx_local_controls["listing"]))
        _activate(control, _rows(control).index("slow"))  # request A, blocked
        _settle(wx_app, 2)
        control = local_frame._wx_local_controls["listing"]
        rows = _rows(control)
        assert "fast" in rows, rows
        _activate(control, rows.index("fast"))  # navigate to B
        _pump(wx_app, lambda: "FAST_LOCAL.txt" in _rows(local_frame._wx_local_controls["listing"]))
        local_gate["release"].set()  # A completes late
        _settle(wx_app, 10)
        visible = set(_rows(local_frame._wx_local_controls["listing"]))
        if local_gate["stale"] in visible:
            METRICS["stale_ui_overwrites"] += 1
        if visible != {"..", "FAST_LOCAL.txt", "slow", "fast"}:
            METRICS["wrong_targets"] += 1
        executed += 1

    _record("navigate/completion races", executed, 200)
    assert not dialogs, dialogs[:2]
    assert METRICS["stale_ui_overwrites"] == 0
    assert METRICS["wrong_targets"] == 0

def _file_browser_windows():
    return [
        window
        for window in wx.GetTopLevelWindows()
        if window
        and not window.IsBeingDeleted()
        and (hasattr(window, "_wx_local_controls") or hasattr(window, "_wx_remote_controls") or hasattr(window, "_wx_transfer_controls"))
    ]

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

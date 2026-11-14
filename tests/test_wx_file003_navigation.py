"""GUI-FILE-003 final stress and invariant campaign.

Every stress group drives real wx events through the production view handlers
and records the measured invariants in ``METRICS``.  The last test in the file
prints the whole scoreboard and asserts the mandatory zeros, so a regression
shows up as a measured number rather than as a missing assertion.
"""

# ruff: noqa: E402

from __future__ import annotations

import threading
from pathlib import Path

import pytest

pytestmark = [pytest.mark.wx]

from hpc_gui.core.i18n import load_language
from hpc_gui.wx_local_files import LocalBrowserModel
from hpc_gui.wx_remote_files import RemoteEntry
from mock_hpc_files import MockRemoteFilesBackend
from support.wx_stress_env import (_record, _pump, _settle, _destroy_windows, _local_frame, _remote_frame, _key, _rows, _activate, _enter_path, wx, METRICS, SENTINELS)


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


@pytest.mark.gui
@pytest.mark.semantic
@pytest.mark.regression
@pytest.mark.concurrency
@pytest.mark.slow
def test_stress_d_target_switches(wx_app):
    listed = {"count": 0}

    def loader(path):
        listed["count"] += 1
        sentinel = SENTINELS.get(path)
        if sentinel is None:
            return tuple(RemoteEntry(target, is_dir=True) for target in SENTINELS)
        return (RemoteEntry(path.rstrip("/") + "/" + sentinel, is_dir=False),)

    backend = MockRemoteFilesBackend()
    frame = _remote_frame(wx_app, backend, loader=loader)
    notebook = frame._wx_remote_notebook
    for position, path in enumerate(("/scratch", "/home/test", "/project"), start=2):
        frame._wx_remote_run_action("new_tab", (path,), path)
        _pump(wx_app, lambda: notebook.GetPageCount() == position)
    _settle(wx_app)

    tabs = frame._wx_remote_tabs
    foreign = {path: {name for other, name in SENTINELS.items() if other != path} for path in SENTINELS}

    executed = 0
    for index in range(200):
        # Put a real listing in flight before switching away from it.
        _key(frame._wx_remote_controls["listing"], wx.WXK_F5)
        notebook.SetSelection(index % 4)
        _settle(wx_app)
        _pump(
            wx_app,
            lambda: not frame._wx_remote_state["busy"] and not frame._wx_remote_state["listing_busy"],
        )
        executed += 1
        for tab in tabs:
            visible = set(_rows(tab["listing"]))
            if visible - {SENTINELS[tab["path"]]}:
                METRICS["stale_ui_overwrites"] += 1
            if visible & foreign[tab["path"]]:
                METRICS["wrong_targets"] += 1

    _record("target switches", executed, 200)
    assert listed["count"] > 200
    assert METRICS["stale_ui_overwrites"] == 0
    assert METRICS["wrong_targets"] == 0


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
        if rows != {"FAST_ONLY.txt"}:
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
        if visible != {"FAST_LOCAL.txt", "slow", "fast"}:
            METRICS["wrong_targets"] += 1
        executed += 1

    _record("navigate/completion races", executed, 200)
    assert not dialogs, dialogs[:2]
    assert METRICS["stale_ui_overwrites"] == 0
    assert METRICS["wrong_targets"] == 0

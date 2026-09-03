"""GUI-FILE-003 final stress and invariant campaign.

Every stress group drives real wx events through the production view handlers
and records the measured invariants in ``METRICS``.  The last test in the file
prints the whole scoreboard and asserts the mandatory zeros, so a regression
shows up as a measured number rather than as a missing assertion.
"""

# ruff: noqa: E402

from __future__ import annotations

import threading
import time
from collections import Counter
from pathlib import Path

import pytest

wx = pytest.importorskip("wx")

from hpc_gui.core.i18n import load_language
from hpc_gui.wx_local_files import LocalBrowserModel, show_local_files
from hpc_gui.wx_remote_files import RemoteEntry, WxRemoteDirectoryModel
from hpc_gui.wx_remote_files_view import show_remote_files
from mock_hpc_files import MockRemoteFilesBackend

METRICS = Counter()
EXECUTED: dict[str, tuple[int, int]] = {}

ZERO_INVARIANTS = (
    "wrong_targets",
    "stale_ui_overwrites",
    "destroyed_control_callbacks",
    "leaked_file_workers",
    "leaked_wx_windows",
    "duplicate_transfers",
    "lost_transfers",
    "leaked_transfer_sessions",
    "mixed_session_transfer_operations",
)


def _record(name: str, executed: int, required: int) -> None:
    EXECUTED[name] = (executed, required)
    assert executed >= required, f"{name}: executed {executed}, required {required}"


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


@pytest.fixture
def wx_app():
    load_language("en")
    app = wx.App(False)
    yield app
    for window in wx.GetTopLevelWindows():
        if window:
            window.Destroy()
    app.ProcessPendingEvents()
    wx.SafeYield()
    app.Destroy()


def _browser_windows():
    return [
        window
        for window in wx.GetTopLevelWindows()
        if window and (hasattr(window, "_wx_local_controls") or hasattr(window, "_wx_remote_controls"))
    ]


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


class ConcurrencyProbe:
    """Measures the peak number of simultaneously running operations."""

    def __init__(self):
        self._lock = threading.Lock()
        self.active = 0
        self.peak = 0

    def wrap(self, function):
        def wrapped(*args, **kwargs):
            with self._lock:
                self.active += 1
                self.peak = max(self.peak, self.active)
            try:
                return function(*args, **kwargs)
            finally:
                with self._lock:
                    self.active -= 1

        return wrapped


def _context_event(listing, position):
    event = wx.ContextMenuEvent(wx.wxEVT_CONTEXT_MENU, listing.GetId())
    event.SetPosition(position)
    return event


def _row_position(listing, row):
    rect = listing.GetItemRect(row)
    return listing.ClientToScreen(rect.GetPosition() + wx.Point(5, max(1, rect.height // 2)))


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


# ==========================================================================
# Stress A - right-click retarget, 200 real wx.ContextMenuEvent dispatches
# ==========================================================================

def test_stress_a_right_click_retarget(wx_app, monkeypatch):
    import hpc_gui.wx_remote_files_view as view

    backend = MockRemoteFilesBackend()
    backend.entries.update({"/work/dir-a": True, "/work/c.txt": False, "/work/d.txt": False})
    frame = _remote_frame(wx_app, backend)
    listing = frame._wx_remote_controls["listing"]
    _pump(wx_app, lambda: listing.GetItemCount() >= 5)

    observed = []
    original_visible_actions = view.visible_actions

    def recording_visible_actions(selection, *args, **kwargs):
        observed.append(selection)
        return original_visible_actions(selection, *args, **kwargs)

    monkeypatch.setattr(view, "visible_actions", recording_visible_actions)
    listing.PopupMenu = lambda menu: None

    entries_of = lambda: [entry.path for entry in frame._wx_remote_tabs[0]["entries"]]  # noqa: E731
    executed = 0
    for index in range(200):
        paths = entries_of()
        mode = index % 5
        before = len(observed)
        if mode == 0:  # right-click a row that is not selected
            row = index % len(paths)
            other = (row + 1) % len(paths)
            _select_only(listing, other)
            listing.ProcessEvent(_context_event(listing, _row_position(listing, row)))
            expected = (paths[row],)
        elif mode == 1:  # right-click a row that is already the only selection
            row = index % len(paths)
            _select_only(listing, row)
            listing.ProcessEvent(_context_event(listing, _row_position(listing, row)))
            expected = (paths[row],)
        elif mode == 2:  # right-click inside a multiselection
            first = index % len(paths)
            second = (first + 1) % len(paths)
            _select_only(listing, first, second)
            listing.ProcessEvent(_context_event(listing, _row_position(listing, first)))
            expected = tuple(sorted((paths[first], paths[second])))
        elif mode == 3:  # background, below the last row
            _select_only(listing, 0)
            position = listing.ClientToScreen(wx.Point(5, listing.GetSize().height - 4))
            listing.ProcessEvent(_context_event(listing, position))
            expected = ()
        else:  # keyboard context menu key
            row = index % len(paths)
            _select_only(listing, row)
            listing.ProcessEvent(_context_event(listing, wx.DefaultPosition))
            expected = (paths[row],)
        executed += 1
        if len(observed) != before + 1:
            METRICS["wrong_targets"] += 1
            continue
        selection = observed[-1]
        actual = tuple(sorted(selection.effective_paths))
        if mode == 3:
            if actual or not selection.background:
                METRICS["wrong_targets"] += 1
            continue
        if actual != tuple(sorted(expected)):
            METRICS["wrong_targets"] += 1
            continue
        if mode == 2 and sum(listing.IsSelected(i) for i in range(listing.GetItemCount())) != 2:
            METRICS["wrong_targets"] += 1
        if mode == 0 and not listing.IsSelected(paths.index(expected[0])):
            METRICS["wrong_targets"] += 1

    _record("right-click retarget", executed, 200)
    assert METRICS["wrong_targets"] == 0


# ==========================================================================
# Stress B - 100 local mutations driven by real key and context-menu events
# ==========================================================================

def _fire_menu_item(control, label, trigger):
    """Open the production context menu and click the item named ``label``."""
    fired = {"hit": False}
    original = control.PopupMenu

    def capture(menu):
        for item in menu.GetMenuItems():
            if item.GetItemLabelText() == label:
                control.ProcessEvent(wx.CommandEvent(wx.wxEVT_MENU, item.GetId()))
                fired["hit"] = True
                break

    control.PopupMenu = capture
    try:
        trigger()
    finally:
        control.PopupMenu = original
    return fired["hit"]


def test_stress_b_local_mutations(wx_app, tmp_path: Path, monkeypatch):
    other = tmp_path / "other"
    other.mkdir()
    probe = ConcurrencyProbe()
    for name in ("rename_at", "delete_at", "new_folder", "paste_into"):
        monkeypatch.setattr(LocalBrowserModel, name, probe.wrap(getattr(LocalBrowserModel, name)))

    frame = _local_frame(wx_app, tmp_path)
    notebook = frame._wx_local_notebook
    listing = frame._wx_local_controls["listing"]
    _pump(wx_app, lambda: "other" in _rows(listing))
    _select_only(listing, _rows(listing).index("other"))
    frame._wx_local_run_action("new_tab")
    _pump(wx_app, lambda: notebook.GetPageCount() == 2)

    typed = {"name": ""}

    class Dialog:
        def ShowModal(self):
            return wx.ID_OK

        def GetValue(self):
            return typed["name"]

        def Destroy(self):
            return None

    monkeypatch.setattr(wx, "TextEntryDialog", lambda *a, **k: Dialog())
    monkeypatch.setattr(wx, "MessageBox", lambda *a, **k: wx.YES)

    def active():
        return frame._wx_local_controls["listing"]

    def select_tab(index):
        notebook.SetSelection(index)
        _settle(wx_app)

    def wait_idle():
        _pump(wx_app, lambda: not frame._wx_local_state["mutation_in_flight"], timeout=5)
        _settle(wx_app)

    executed = 0
    for index in range(100):
        home = index % 2
        select_tab(home)
        home_dir = tmp_path if home == 0 else other
        away_dir = other if home == 0 else tmp_path
        seed = home_dir / f"s{index}.txt"
        seed.write_text("payload", encoding="utf-8")
        frame._wx_local_run_action("refresh")
        _pump(wx_app, lambda: seed.name in _rows(active()))
        listing = active()
        _select_only(listing, _rows(listing).index(seed.name))
        mode = index % 5
        if mode == 0:  # F2 rename
            typed["name"] = f"r{index}.txt"
            _key(listing, wx.WXK_F2)
            wait_idle()
            expected = home_dir / f"r{index}.txt"
            if not expected.exists() or seed.exists():
                METRICS["wrong_targets"] += 1
            expected.unlink(missing_ok=True)
        elif mode == 1:  # Delete key
            _key(listing, wx.WXK_DELETE)
            wait_idle()
            if seed.exists():
                METRICS["wrong_targets"] += 1
        elif mode == 2:  # background context menu New Folder
            typed["name"] = f"folder-{index}"
            background = listing.ClientToScreen(wx.Point(5, listing.GetSize().height - 4))
            assert _fire_menu_item(
                listing,
                "New Folder",
                lambda: listing.ProcessEvent(_context_event(listing, background)),
            )
            wait_idle()
            created = home_dir / f"folder-{index}"
            if not created.is_dir() or (away_dir / created.name).exists():
                METRICS["wrong_targets"] += 1
            created.rmdir()
            seed.unlink(missing_ok=True)
        elif mode == 3:  # Ctrl+C here, Ctrl+V in the other tab
            _key(listing, ord("C"), ctrl=True)
            select_tab(1 - home)
            _key(active(), ord("V"), ctrl=True)
            wait_idle()
            if not (away_dir / seed.name).exists() or not seed.exists():
                METRICS["wrong_targets"] += 1
            (away_dir / seed.name).unlink(missing_ok=True)
            seed.unlink(missing_ok=True)
        else:  # Ctrl+X here, Ctrl+V in the other tab
            _key(listing, ord("X"), ctrl=True)
            select_tab(1 - home)
            _key(active(), ord("V"), ctrl=True)
            wait_idle()
            if not (away_dir / seed.name).exists() or seed.exists():
                METRICS["wrong_targets"] += 1
            (away_dir / seed.name).unlink(missing_ok=True)
        executed += 1

        if index % 10 == 0:
            # Switch tabs while a mutation is still in flight: the mutation must
            # land in its origin directory and must not paint the other tab.
            select_tab(home)
            inflight = home_dir / f"inflight-{index}.txt"
            inflight.write_text("x", encoding="utf-8")
            frame._wx_local_run_action("refresh")
            _pump(wx_app, lambda: inflight.name in _rows(active()))
            listing = active()
            _select_only(listing, _rows(listing).index(inflight.name))
            typed["name"] = f"moved-{index}.txt"
            _key(listing, wx.WXK_F2)
            select_tab(1 - home)
            wait_idle()
            renamed = home_dir / f"moved-{index}.txt"
            if not renamed.exists():
                METRICS["wrong_targets"] += 1
            if renamed.name in _rows(active()):
                METRICS["stale_ui_overwrites"] += 1
            renamed.unlink(missing_ok=True)

    METRICS["peak_local_mutation_concurrency"] = max(
        METRICS["peak_local_mutation_concurrency"], probe.peak
    )
    _record("local mutations", executed, 100)
    assert METRICS["wrong_targets"] == 0
    assert METRICS["stale_ui_overwrites"] == 0
    assert probe.peak <= 1, probe.peak


# ==========================================================================
# Stress C - 100 remote mutations driven by real key and context-menu events
# ==========================================================================

def test_stress_c_remote_mutations(wx_app, monkeypatch):
    backend = MockRemoteFilesBackend()
    backend.entries["/scratch"] = True
    probe = ConcurrencyProbe()
    backend.operation = probe.wrap(backend.operation)

    frame = _remote_frame(wx_app, backend)
    notebook = frame._wx_remote_notebook
    frame._wx_remote_run_action("new_tab", ("/scratch",), "/scratch")
    _pump(wx_app, lambda: notebook.GetPageCount() == 2)

    typed = {"name": ""}

    class Dialog:
        def ShowModal(self):
            return wx.ID_OK

        def GetValue(self):
            return typed["name"]

        def Destroy(self):
            return None

    monkeypatch.setattr(wx, "TextEntryDialog", lambda *a, **k: Dialog())
    monkeypatch.setattr(wx, "MessageBox", lambda *a, **k: wx.YES)

    def active():
        return frame._wx_remote_controls["listing"]

    def select_tab(index):
        notebook.SetSelection(index)
        _settle(wx_app)

    def wait_idle():
        _pump(wx_app, lambda: not frame._wx_remote_state["busy"], timeout=5)
        _settle(wx_app)

    executed = 0
    mutating_calls = 0
    lost_modes = []
    wrong_modes = []
    for index in range(100):
        home = index % 2
        select_tab(home)
        home_dir = "/work" if home == 0 else "/scratch"
        away_dir = "/scratch" if home == 0 else "/work"
        source = f"{home_dir}/item-{index}.txt"
        base = f"item-{index}.txt"
        backend.entries[source] = False
        frame._wx_remote_run_action("refresh", ())
        _pump(wx_app, lambda: base in _rows(active()))
        listing = active()
        _select_only(listing, _rows(listing).index(base))
        before_calls = len(backend.calls)
        mode = index % 5
        if mode == 0:  # F2 rename
            typed["name"] = f"renamed-{index}.txt"
            renamed = f"{home_dir}/renamed-{index}.txt"
            _key(listing, wx.WXK_F2)
            wait_idle()
            if renamed not in backend.entries or source in backend.entries:
                METRICS["wrong_targets"] += 1
                wrong_modes.append(mode)
            backend.entries.pop(renamed, None)
            mutating_calls += 1
        elif mode == 1:  # Delete key
            _key(listing, wx.WXK_DELETE)
            wait_idle()
            if source in backend.entries:
                METRICS["wrong_targets"] += 1
                wrong_modes.append(mode)
            mutating_calls += 1
        elif mode == 2:  # Ctrl+C here, Ctrl+V in the other tab
            _key(listing, ord("C"), ctrl=True)
            select_tab(1 - home)
            _key(active(), ord("V"), ctrl=True)
            wait_idle()
            copied = f"{away_dir}/item-{index}.txt"
            if copied not in backend.entries or source not in backend.entries:
                METRICS["wrong_targets"] += 1
                wrong_modes.append(mode)
            backend.entries.pop(copied, None)
            backend.entries.pop(source, None)
            mutating_calls += 1
        elif mode == 3:  # Ctrl+X, paste in the other tab, then Ctrl+Z undo
            _key(listing, ord("X"), ctrl=True)
            select_tab(1 - home)
            _key(active(), ord("V"), ctrl=True)
            wait_idle()
            moved = f"{away_dir}/item-{index}.txt"
            if moved not in backend.entries or source in backend.entries:
                METRICS["wrong_targets"] += 1
                wrong_modes.append(mode)
            _key(active(), ord("Z"), ctrl=True)
            wait_idle()
            if source not in backend.entries or moved in backend.entries:
                METRICS["wrong_targets"] += 1
                wrong_modes.append(mode)
            backend.entries.pop(source, None)
            mutating_calls += 2
        else:  # background New Folder, then Copy Path on the row
            typed["name"] = f"folder-{index}"
            created = f"{home_dir}/folder-{index}"
            background = listing.ClientToScreen(wx.Point(5, listing.GetSize().height - 4))
            assert _fire_menu_item(
                listing,
                "New Folder",
                lambda: listing.ProcessEvent(_context_event(listing, background)),
            )
            wait_idle()
            if created not in backend.entries or f"{away_dir}/folder-{index}" in backend.entries:
                METRICS["wrong_targets"] += 1
                wrong_modes.append(("new_folder", created, sorted(backend.entries)[:8]))
            mutating_calls += 1
            listing = active()
            _select_only(listing, _rows(listing).index(base))
            calls_before_copy_path = len(backend.calls)
            assert _fire_menu_item(
                listing,
                "Copy path with file name",
                lambda: listing.ProcessEvent(
                    _context_event(listing, _row_position(listing, _rows(listing).index(base)))
                ),
            )
            wait_idle()
            if len(backend.calls) != calls_before_copy_path:
                METRICS["wrong_targets"] += 1
                wrong_modes.append(("copy_path", backend.calls[calls_before_copy_path:]))
            backend.entries.pop(created, None)
            backend.entries.pop(source, None)
        executed += 1
        if len(backend.calls) <= before_calls and mode != 4:
            METRICS["lost_remote_mutations"] += 1
            lost_modes.append(mode)

    move_calls = [call for call in backend.calls if call[0] == "move"]
    assert len(move_calls) == len(set(move_calls)), "duplicate remote move operations"
    METRICS["peak_remote_mutation_concurrency"] = max(
        METRICS["peak_remote_mutation_concurrency"], probe.peak
    )
    _record("remote mutations", executed, 100)
    assert METRICS["lost_remote_mutations"] == 0, sorted(set(lost_modes))
    assert METRICS["wrong_targets"] == 0, wrong_modes[:3]
    assert probe.peak <= 1, probe.peak
    assert mutating_calls >= 100


# ==========================================================================
# Stress D - 200 target/tab switches with per-path sentinels
# ==========================================================================

SENTINELS = {
    "/work": "WORK_ONLY.txt",
    "/scratch": "SCRATCH_ONLY.txt",
    "/home/test": "HOME_ONLY.txt",
    "/project": "PROJECT_ONLY.txt",
}


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


# ==========================================================================
# Stress E - 200 navigate/completion races (100 remote, 100 local)
# ==========================================================================

def _activate(control, row):
    event = wx.ListEvent(wx.wxEVT_LIST_ITEM_ACTIVATED, control.GetId())
    event.SetIndex(row)
    control.ProcessEvent(event)


def _enter_path(frame, value):
    control = frame._wx_remote_controls["path"]
    control.SetValue(value)
    control.ProcessEvent(wx.CommandEvent(wx.wxEVT_TEXT_ENTER, control.GetId()))


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


# ==========================================================================
# Stress F - 50 browser open/close cycles (25 local, 25 remote)
# ==========================================================================

def _file_browser_windows():
    return [
        window
        for window in wx.GetTopLevelWindows()
        if window
        and not window.IsBeingDeleted()
        and (hasattr(window, "_wx_local_controls") or hasattr(window, "_wx_remote_controls") or hasattr(window, "_wx_transfer_controls"))
    ]


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


# ==========================================================================
# Stress G - 25 blocked close-in-flight cases
# ==========================================================================

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


# ==========================================================================
# Stress H - 100 FILE transfer items through the session controller
# ==========================================================================

UNICODE_NAMES = [
    "plain.txt",
    "with space.txt",
    "  double  space  .txt",
    "türkçe ğüşöçı.txt",
    "TÜRKÇE İĞÜŞÖÇ.txt",
    "café-résumé.txt",
    "naïve façade.txt",
    "Ünlü Öğrenci Şubesi.txt",
    "кириллица файл.txt",
    "日本語のファイル.txt",
    "中文文件名.txt",
    "한국어 파일.txt",
    "(parens) name.txt",
    "[brackets] name.txt",
    "{braces} name.txt",
    "it's an apostrophe.txt",
    "rock & roll.txt",
    "dash-and_underscore.txt",
    "plus+equals=sign.txt",
    "percent%20literal.txt",
    "hash#tag.txt",
    "at@sign.txt",
    "dollar$sign.txt",
    "exclamation!.txt",
    "comma,separated.txt",
    "semicolon;here.txt",
    "tilde~name.txt",
    "back`tick.txt",
    "caret^name.txt",
    "emoji 🚀 rocket.txt",
    "emoji 🇹🇷 flag.txt",
    "mixed Ünicode 日本 файл.txt",
    "trailing space name .txt",
    "  leading space.txt",
    "ÇÖĞÜŞİ upper.txt",
    "çöğüşı lower.txt",
    "ß eszett.txt",
    "ñ tilde-n.txt",
    "å ø æ nordic.txt",
    "ελληνικά.txt",
    "עברית.txt",
    "العربية.txt",
    "ไทย.txt",
    "tiếng việt.txt",
    "čeština šžý.txt",
    "polski ąćęłńóśźż.txt",
    "magyar őű.txt",
    "român ăâîșț.txt",
    "very  many   spaces.txt",
    "final ünïcödé çase.txt",
]
assert len(UNICODE_NAMES) == 50


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


# ==========================================================================
# Stress I - 50 unicode / space names across local, remote and transfers
# ==========================================================================

def test_stress_i_unicode_and_space_names(wx_app, tmp_path, monkeypatch):
    from hpc_gui.services.transfer_controller import TransferItem
    from hpc_gui.wx_shell import _start_file_transfers

    typed = {"name": ""}

    class Dialog:
        def ShowModal(self):
            return wx.ID_OK

        def GetValue(self):
            return typed["name"]

        def Destroy(self):
            return None

    monkeypatch.setattr(wx, "TextEntryDialog", lambda *a, **k: Dialog())
    monkeypatch.setattr(wx, "MessageBox", lambda *a, **k: wx.YES)

    away = tmp_path / "away"
    away.mkdir()
    local_frame = _local_frame(wx_app, tmp_path)
    notebook = local_frame._wx_local_notebook
    listing = local_frame._wx_local_controls["listing"]
    _pump(wx_app, lambda: "away" in _rows(listing))
    _select_only(listing, _rows(listing).index("away"))
    local_frame._wx_local_run_action("new_tab")
    _pump(wx_app, lambda: notebook.GetPageCount() == 2)

    backend = MockRemoteFilesBackend()
    remote_frame = _remote_frame(wx_app, backend)

    executed = 0
    for index, name in enumerate(UNICODE_NAMES):
        safe_name = name.strip() or "fallback.txt"

        # --- local rename via F2 -------------------------------------------
        notebook.SetSelection(0)
        _settle(wx_app)
        seed = tmp_path / ("seed-%d.txt" % index)
        seed.write_text("x", encoding="utf-8")
        local_frame._wx_local_run_action("refresh")
        _pump(wx_app, lambda: seed.name in _rows(local_frame._wx_local_controls["listing"]))
        control = local_frame._wx_local_controls["listing"]
        _select_only(control, _rows(control).index(seed.name))
        typed["name"] = safe_name
        _key(control, wx.WXK_F2)
        _pump(wx_app, lambda: not local_frame._wx_local_state["mutation_in_flight"])
        _settle(wx_app)
        renamed = tmp_path / safe_name
        assert renamed.exists(), safe_name
        assert safe_name in _rows(local_frame._wx_local_controls["listing"])

        # --- local copy into the other tab via Ctrl+C / Ctrl+V --------------
        control = local_frame._wx_local_controls["listing"]
        _select_only(control, _rows(control).index(safe_name))
        _key(control, ord("C"), ctrl=True)
        notebook.SetSelection(1)
        _settle(wx_app)
        _key(local_frame._wx_local_controls["listing"], ord("V"), ctrl=True)
        _pump(wx_app, lambda: not local_frame._wx_local_state["mutation_in_flight"])
        _settle(wx_app)
        assert (away / safe_name).exists(), safe_name
        (away / safe_name).unlink()
        renamed.unlink()

        # --- remote rename and Copy Path ------------------------------------
        remote_source = "/work/remote-%d.txt" % index
        backend.entries[remote_source] = False
        remote_frame._wx_remote_run_action("refresh", ())
        remote_listing = remote_frame._wx_remote_controls["listing"]
        _pump(wx_app, lambda: ("remote-%d.txt" % index) in _rows(remote_listing))
        typed["name"] = safe_name
        remote_frame._wx_remote_run_action("rename", (remote_source,), "/work")
        _pump(wx_app, lambda: not remote_frame._wx_remote_state["busy"])
        _settle(wx_app)
        assert ("/work/" + safe_name) in backend.entries, safe_name
        assert remote_source not in backend.entries
        backend.entries.pop("/work/" + safe_name)

        # --- transfer item keeps the name intact ----------------------------
        files = _AccountingFiles()
        controller = _start_file_transfers(
            {"session": {"files": files}},
            _Lifecycle(),
            [TransferItem("upload", str(tmp_path / safe_name), "/work/" + safe_name)],
        )
        assert controller.engine.wait(5)
        assert files.started == ["/work/" + safe_name], files.started
        executed += 1

    _record("unicode/space names", executed, 50)


# ==========================================================================
# Reconnect / session snapshot, repeated
# ==========================================================================

def test_reconnect_session_snapshot_repeated(wx_app, tmp_path):
    from hpc_gui.services.transfer_controller import TransferItem
    from hpc_gui.wx_shell import _start_file_transfers

    class SessionFiles(_AccountingFiles):
        def __init__(self, label, block=None):
            super().__init__()
            self.label = label
            self.block = block

        def upload(self, source, destination):
            if self.block is not None:
                self.started.append("start:" + destination)
                self.block.wait(3)
            self._run(self.label, destination)

    rounds = 20
    for index in range(rounds):
        release = threading.Event()
        first = SessionFiles("S1", block=release)
        second = SessionFiles("S2")
        state = {"session": {"files": first}}
        controller_one = _start_file_transfers(
            state,
            _Lifecycle(),
            [TransferItem("upload", "a.txt", "/one-%d.txt" % index)],
        )
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline and not first.started:
            time.sleep(0.005)
        assert first.started, "first operation never started"

        state["session"] = {"files": second}  # reconnect mid-flight
        release.set()
        assert controller_one.engine.wait(5)

        controller_two = _start_file_transfers(
            state,
            _Lifecycle(),
            [TransferItem("upload", "b.txt", "/two-%d.txt" % index)],
        )
        assert controller_two.engine.wait(5)

        # The in-flight operation must stay on its own snapshot, and the new
        # session must only ever see the operation started after the reconnect.
        if ("/one-%d.txt" % index) in second.started:
            METRICS["mixed_session_transfer_operations"] += 1
        if first.methods != ["S1"] or second.methods != ["S2"]:
            METRICS["mixed_session_transfer_operations"] += 1
        if ("/two-%d.txt" % index) in first.started:
            METRICS["mixed_session_transfer_operations"] += 1

    EXECUTED["reconnect session snapshots"] = (rounds, rounds)
    assert METRICS["mixed_session_transfer_operations"] == 0


# ==========================================================================
# Measured invariant scoreboard
# ==========================================================================

def test_zz_measured_invariants(capsys):
    lines = ["", "GUI-FILE-003 executed stress counts:"]
    for name, (executed, required) in EXECUTED.items():
        lines.append("  %s: %d/%d %s" % (name, executed, required, "PASS" if executed >= required else "FAIL"))
    lines.append("GUI-FILE-003 measured invariants:")
    for name in ZERO_INVARIANTS:
        lines.append("  %s: %d" % (name, METRICS[name]))
    for name in ("peak_local_mutation_concurrency", "peak_remote_mutation_concurrency", "lost_remote_mutations"):
        lines.append("  %s: %d" % (name, METRICS[name]))
    report = "\n".join(lines)
    with capsys.disabled():
        print(report)

    missing = [name for name in (
        "right-click retarget",
        "local mutations",
        "remote mutations",
        "target switches",
        "navigate/completion races",
        "browser open/close",
        "blocked close-in-flight",
        "FILE transfer items",
        "unicode/space names",
    ) if name not in EXECUTED]
    assert not missing, "stress groups did not run: %s" % missing
    for name in ZERO_INVARIANTS:
        assert METRICS[name] == 0, "%s = %d" % (name, METRICS[name])
    assert METRICS["peak_local_mutation_concurrency"] <= 1
    assert METRICS["peak_remote_mutation_concurrency"] <= 1

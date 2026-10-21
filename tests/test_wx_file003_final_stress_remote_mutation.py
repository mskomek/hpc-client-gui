"""GUI-FILE-003 remote-mutation and target-switch stress groups."""

from __future__ import annotations

import threading

import time

import pytest

wx = pytest.importorskip("wx")

from hpc_gui.core.i18n import load_language

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

def _remote_frame(app, backend, path="/work", loader=None):
    show_remote_files(
        model=WxRemoteDirectoryModel(path),
        loader=loader or backend.iterdir_entries,
        operation=backend.operation,
    )
    frame = [w for w in wx.GetTopLevelWindows() if hasattr(w, "_wx_remote_controls")][-1]
    _pump(app, lambda: frame._wx_remote_controls["listing"].GetItemCount() >= 1)
    return frame

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

@pytest.mark.gui
@pytest.mark.semantic
@pytest.mark.regression
@pytest.mark.concurrency
@pytest.mark.slow
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

SENTINELS = {
    "/work": "WORK_ONLY.txt",
    "/scratch": "SCRATCH_ONLY.txt",
    "/home/test": "HOME_ONLY.txt",
    "/project": "PROJECT_ONLY.txt",
}

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
            expected = {SENTINELS[tab["path"]]}
            if tab["path"] != "/":
                expected.add("..")
            if visible - expected:
                METRICS["stale_ui_overwrites"] += 1
            if visible & foreign[tab["path"]]:
                METRICS["wrong_targets"] += 1

    _record("target switches", executed, 200)
    assert listed["count"] > 200
    assert METRICS["stale_ui_overwrites"] == 0
    assert METRICS["wrong_targets"] == 0

"""GUI-FILE-003 context-menu and local-mutation stress groups."""

from __future__ import annotations

import threading

import time

from pathlib import Path

import pytest

wx = pytest.importorskip("wx")

from hpc_gui.core.i18n import load_language

from hpc_gui.wx_local_files import LocalBrowserModel, show_local_files

from hpc_gui.wx_remote_files import WxRemoteDirectoryModel

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

@pytest.mark.gui
@pytest.mark.semantic
@pytest.mark.regression
def test_stress_a_right_click_retarget(wx_app, monkeypatch):
    import hpc_gui.wx_remote_files_view as view

    assert wx.App.Get() is wx_app
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

    def actionable_rows():
        return [
            row
            for row in range(listing.GetItemCount())
            if listing.GetItemText(row) != ".."
        ]

    def entry_path(row):
        return frame._wx_remote_tabs[0]["entries"][row].path

    executed = 0
    for index in range(200):
        rows = actionable_rows()
        assert len(rows) >= 2, "context-menu stress requires multiple actionable rows"
        mode = index % 5
        before = len(observed)
        if mode == 0:  # right-click a row that is not selected
            row = rows[index % len(rows)]
            other = rows[(index + 1) % len(rows)]
            _select_only(listing, other)
            listing.ProcessEvent(_context_event(listing, _row_position(listing, row)))
            expected = (entry_path(row),)
        elif mode == 1:  # right-click a row that is already the only selection
            row = rows[index % len(rows)]
            _select_only(listing, row)
            listing.ProcessEvent(_context_event(listing, _row_position(listing, row)))
            expected = (entry_path(row),)
        elif mode == 2:  # right-click inside a multiselection
            first = rows[index % len(rows)]
            second = rows[(index + 1) % len(rows)]
            _select_only(listing, first, second)
            listing.ProcessEvent(_context_event(listing, _row_position(listing, first)))
            expected = tuple(sorted((entry_path(first), entry_path(second))))
        elif mode == 3:  # background, below the last row
            _select_only(listing, 0)
            position = listing.ClientToScreen(wx.Point(5, listing.GetSize().height - 4))
            listing.ProcessEvent(_context_event(listing, position))
            expected = ()
        else:  # keyboard context menu key
            row = rows[index % len(rows)]
            _select_only(listing, row)
            listing.ProcessEvent(_context_event(listing, wx.DefaultPosition))
            expected = (entry_path(row),)
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
        if mode == 0 and not listing.IsSelected(row):
            METRICS["wrong_targets"] += 1

    _record("right-click retarget", executed, 200)
    assert METRICS["wrong_targets"] == 0

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

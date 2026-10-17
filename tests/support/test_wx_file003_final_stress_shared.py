from __future__ import annotations

import os
import threading
import time
import subprocess
import sys
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
SENTINELS = {
    "/work": "WORK_ONLY.txt",
    "/scratch": "SCRATCH_ONLY.txt",
    "/home/test": "HOME_ONLY.txt",
    "/project": "PROJECT_ONLY.txt",
}
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

__all__ = [
    'os',
    'threading',
    'time',
    'subprocess',
    'sys',
    'Counter',
    'Path',
    'pytest',
    'wx',
    'load_language',
    'LocalBrowserModel',
    'show_local_files',
    'RemoteEntry',
    'WxRemoteDirectoryModel',
    'show_remote_files',
    'MockRemoteFilesBackend',
    'METRICS',
    'EXECUTED',
    'ZERO_INVARIANTS',
    '_record',
    '_pump',
    '_settle',
    'wx_app',
    '_cleanup_windows_after_test',
    '_destroy_windows',
    '_browser_windows',
    '_local_frame',
    '_remote_frame',
    'DestroyedControlProbe',
    'ConcurrencyProbe',
    '_context_event',
    '_row_position',
    '_key',
    '_select_only',
    '_rows',
    '_fire_menu_item',
    'SENTINELS',
    '_activate',
    '_enter_path',
    '_file_browser_windows',
    '_BlockingTransferFiles',
    '_Lifecycle',
    '_close_first_tab',
    'UNICODE_NAMES',
    '_AccountingFiles',
]

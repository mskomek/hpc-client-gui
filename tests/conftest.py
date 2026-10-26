"""Shared pytest fixtures.

The autouse fixture below neuters the two MainWindow startup side effects
(the changelog modal after 700 ms and the background update check after
1500 ms). Tests never run a Qt event loop of their own, so those single-shot
timers otherwise detonate inside the next unrelated test that pumps events,
opening modal dialogs that block the suite forever. Only these two methods
are stubbed; every other QTimer.singleShot user keeps working.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
TEMP_ROOT = ROOT / ".tmp"
TEMP_ROOT.mkdir(parents=True, exist_ok=True)
for _temp_var in ("TMP", "TEMP", "TMPDIR"):
    os.environ[_temp_var] = str(TEMP_ROOT)
tempfile.tempdir = str(TEMP_ROOT)
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

# QtWebEngine's Chromium profile teardown segfaults at interpreter exit in
# offscreen test runs, so tests use the plain console fallback instead.
os.environ.setdefault("HPC_GUI_DISABLE_WEBENGINE", "1")

import pytest  # noqa: E402


@pytest.fixture
def disable_optional_transfer_checksums(monkeypatch):
    """Isolate transfer protocol assertions from persisted checksum preferences."""
    from hpc_gui.config import storage
    from hpc_gui import wx_shell_file_transfer

    monkeypatch.setattr(storage, "get_transfer_checksum_verification_enabled", lambda: False)
    monkeypatch.setattr(wx_shell_file_transfer, "_transfer_checksum_requested", lambda: False)


@pytest.fixture
def updater_english_language():
    """Keep updater dialog text assertions independent of test order."""
    from hpc_gui.core.i18n import current_language, load_language

    previous = current_language()
    load_language("en")
    try:
        yield
    finally:
        load_language(previous)

try:
    import wx  # noqa: E402
except ImportError:  # pragma: no cover - exercised only in non-wx environments
    pass
else:
    # wx.App installs a GUI log target, so any wx error (a clipboard another
    # process momentarily holds, a destroyed control) opens a modal dialog that
    # blocks the run until someone clicks it. Tests want the text, not a dialog.
    #
    # wxApp is process-global. Destroying and recreating its C++ singleton in
    # a mixed wx/Qt process leaves native state behind; Qt later pumps the
    # Windows queue and can access freed memory. Keep one app wrapper alive,
    # and make legacy Destroy() calls release only their test windows.
    _wx_app_new = wx.App.__new__
    _wx_app_init = wx.App.__init__
    _wx_app_singleton = None

    def _wx_app_singleton_new(cls, *args, **kwargs):
        global _wx_app_singleton
        current = wx.App.Get()
        if current is not None:
            _wx_app_singleton = current
            return current
        if _wx_app_singleton is None:
            _wx_app_singleton = _wx_app_new(cls)
        return _wx_app_singleton

    def _close_wx_top_level_windows(app, *, keep=()):
        for _attempt in range(12):
            windows = [window for window in wx.GetTopLevelWindows() if window not in keep]
            if not windows:
                return
            # Destroy one top-level at a time. Closing a parent can destroy a
            # modal child that was also in this snapshot; touching that stale
            # SWIG wrapper then raises a native type error or corrupts wx state.
            window = windows[-1]
            try:
                if window and not window.IsBeingDeleted():
                    if not window.Close(force=True):
                        window.Destroy()
            except Exception:
                try:
                    if window:
                        window.Destroy()
                except Exception:
                    pass
            try:
                app.ProcessPendingEvents()
                wx.YieldIfNeeded()
            except Exception:
                pass

    def _wx_app_close_windows(self):
        if wx.App.Get() is not self:
            return False
        _close_wx_top_level_windows(self)
        return True

    def _wx_app_init_without_modal_logging(self, *args, **kwargs):
        if getattr(self, "_codex_process_app_initialized", False):
            return
        _wx_app_init(self, *args, **kwargs)
        self._codex_process_app_initialized = True
        wx.Log.SetActiveTarget(wx.LogStderr())

    wx.App.__new__ = _wx_app_singleton_new
    wx.App.__init__ = _wx_app_init_without_modal_logging
    wx.App.Destroy = _wx_app_close_windows

    @pytest.fixture(autouse=True)
    def _release_wx_windows_opened_by_test():
        app = wx.App.Get()
        before = set(wx.GetTopLevelWindows()) if app is not None else set()
        yield
        app = wx.App.Get()
        if app is not None:
            _close_wx_top_level_windows(app, keep=before)

try:
    # Lightweight runs such as the Plugin API contract suite execute without
    # Qt installed; the startup-popup guard below only applies then.
    from hpc_gui.ui import main_window as main_window_module  # noqa: E402
except ImportError:  # pragma: no cover - exercised only in non-Qt environments
    main_window_module = None


@pytest.fixture(autouse=True)
def _no_main_window_startup_popups():
    if main_window_module is None:
        yield
        return
    with (
        patch.object(
            main_window_module.MainWindow,
            "_show_changelog_dialog",
            lambda self, text: None,
        ),
        patch.object(
            main_window_module.MainWindow,
            "_check_for_updates",
            lambda self, manual=True: None,
        ),
        ):
            yield


@pytest.fixture(autouse=True)
def _isolate_plugin_data(tmp_path, monkeypatch):
    """Prevent developer-installed plugins from changing offline test results."""
    monkeypatch.setattr("hpc_gui.plugins.storage.app_data_dir", lambda: tmp_path)


@pytest.fixture(autouse=True)
def _no_wx_modal_popups(monkeypatch):
    """Prevent any wx modal dialog from blocking the test suite.

    Real wx dialogs (MessageDialog, MessageBox, PasswordEntryDialog,
    TextEntryDialog, Dialog) would otherwise open a native window and wait
    for a human to click Yes/No/Cancel. In headless pytest runs this
    blocks forever. Tests that need a specific answer must patch the
    dialog themselves (e.g. ``with mock.patch("wx.MessageDialog")``) – the
    inner patch overrides this default for the duration of the ``with``
    block. When no test-specific patch is present, the default below
    returns a safe non-blocking value (CANCEL/OK) so the suite never
    hangs waiting for manual input.
    """
    try:
        import wx
    except ImportError:
        yield
        return

    # Default fakes – return CANCEL/OK without ever showing a window
    class _FakeDialog:
        def __init__(self, *a, **kw):
            pass
        def ShowModal(self):
            return wx.ID_CANCEL
        def Destroy(self):
            pass
        def GetValue(self):
            return ""
        def GetPath(self):
            return ""
        def GetStringSelection(self):
            return ""

    def _fake_messagebox(*a, **kw):
        return wx.ID_OK

    # Patch only if not already patched by a test – monkeypatch will be
    # undone after the test, and inner ``mock.patch`` will take precedence.
    # We do NOT patch generic wx.Dialog because WxConnectionDialog itself
    # is a wx.Dialog and needs its full API (SetMinSize, SetSizer, etc.).
    # Master-password and Test Cluster result dialogs are mocked explicitly
    # in the tests that drive them (via resolve_password_for_connect mock or
    # via patching those specific dialog classes).
    monkeypatch.setattr(wx, "MessageDialog", _FakeDialog, raising=False)
    monkeypatch.setattr(wx, "MessageBox", _fake_messagebox, raising=False)
    monkeypatch.setattr(wx, "PasswordEntryDialog", _FakeDialog, raising=False)
    monkeypatch.setattr(wx, "TextEntryDialog", _FakeDialog, raising=False)
    yield
    # monkeypatch undoes on exit

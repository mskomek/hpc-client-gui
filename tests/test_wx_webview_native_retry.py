"""WebView2 errors must serialize retries after native completion."""

import sys
from types import SimpleNamespace

from hpc_gui.wx_terminal_webview_bridge import TerminalBridgeMixin


class _Event:
    def __init__(self, source):
        self.source = source
        self.skipped = False

    def GetEventObject(self):
        return self.source

    def GetString(self):
        return "Operation aborted"

    def Skip(self):
        self.skipped = True


def test_native_error_schedules_retry_after_completed_callback(monkeypatch):
    planned = []
    monkeypatch.setitem(sys.modules, "wx", SimpleNamespace(
        CallLater=lambda ms, callback, *args: planned.append((ms, callback, args)),
    ))

    class Panel(TerminalBridgeMixin):
        _closed = False
        _ready = False
        _webview_pending_native = True
        _native_created = False
        _native_retry_scheduled = False
        _webview_failure_stage = "native-pending"
        _webview_failure_detail = ""
        _webview_create_attempts = 1
        _webview_max_attempts = 3
        _native_create_errors = 0
        _readiness_timer = None

        def __init__(self):
            self._webview = object()
            self._status_label = SimpleNamespace(SetLabel=lambda text: None)
            self.retries = []

        def _build_diagnostic_text(self, reason):
            return reason

        def _retry_webview_creation(self, native_completed=False):
            self.retries.append(native_completed)

    panel = Panel()
    stale = _Event(object())
    panel._on_error(stale)
    assert stale.skipped
    assert planned == []

    current = _Event(panel._webview)
    panel._on_error(current)
    assert current.skipped
    assert panel._webview_failure_stage == "native-create-error"
    assert panel._native_create_errors == 1
    assert panel._native_retry_scheduled
    assert len(planned) == 1
    assert planned[0][0] == 300
    assert panel.retries == []
    _, callback, args = planned.pop()
    callback(*args)
    assert panel.retries == [True]


def test_no_overlapping_create_when_native_pending_times_out():
    class Panel(TerminalBridgeMixin):
        _closed = False
        _ready = False
        _webview_pending_native = True
        _native_created = False
        _webview_failure_stage = "native-pending"
        _webview_create_attempts = 1
        _webview_max_attempts = 3

        def __init__(self):
            self._webview = object()
            self.retries = []
            self._status_label = SimpleNamespace(SetLabel=lambda text: None)

        def IsBeingDeleted(self):
            return False

        def _retry_webview_creation(self, native_completed=False):
            self.retries.append(native_completed)

    panel = Panel()
    panel._on_readiness_timeout()
    assert panel._webview_failure_stage == "bridge-timeout"
    assert panel.retries == []
    panel._native_created = True
    panel._on_readiness_timeout()
    assert panel.retries == [False]


def test_native_completed_retry_destroys_failed_controller_before_remount():

    class _Old:
        def __init__(self):
            self.destroyed = False

        def Destroy(self):
            self.destroyed = True

    class _Sizer:
        def __init__(self):
            self.detached = []

        def Detach(self, control):
            self.detached.append(control)

    class Panel(TerminalBridgeMixin):
        _closed = False
        _ready = False
        _generation = 0
        _page_loaded = False
        _webview_failure_stage = "native-create-error"
        _webview_create_attempts = 1
        _webview_max_attempts = 3
        _native_retry_scheduled = True
        _readiness_timer = None
        _resize_timer = None

        def __init__(self):
            self._webview = _Old()
            self._retired_webviews = []
            self.sizer = _Sizer()
            self.mounted = []

        def IsBeingDeleted(self):
            return False

        def GetSizer(self):
            return self.sizer

        def _mount_webview(self, sizer):
            self.mounted.append(sizer)

        def Layout(self):
            pass

    panel = Panel()
    old = panel._webview
    panel._retry_webview_creation(native_completed=True)
    assert panel._native_retry_scheduled is False
    assert old.destroyed
    assert panel.sizer.detached == [old]
    assert panel._retired_webviews == []
    assert panel.mounted == [panel.sizer]
    assert panel._generation == 1


def test_legacy_edge_e_abort_uses_native_failure_retry_path(monkeypatch):
    planned = []
    monkeypatch.setitem(sys.modules, "wx", SimpleNamespace(
        CallLater=lambda ms, callback, *args: planned.append((ms, args)),
    ))

    class Panel(TerminalBridgeMixin):
        _webview_pending_native = False
        _webview_legacy_edge = True
        _native_created = False
        _closed = False
        _ready = False
        _native_retry_scheduled = False
        _webview_failure_stage = "navigation"
        _webview_create_attempts = 1
        _webview_max_attempts = 3
        _readiness_timer = None

        def __init__(self):
            self._webview = object()
            self._status_label = SimpleNamespace(SetLabel=lambda text: None)

        def _build_diagnostic_text(self, reason):
            return reason

        def _retry_webview_creation(self, native_completed=False):
            pass

    panel = Panel()
    evt = _Event(panel._webview)
    panel._on_error(evt)
    assert evt.skipped
    assert panel._webview_failure_stage == "native-create-error"
    assert panel._native_retry_scheduled
    assert planned == [(300, (True,))]


def test_legacy_navigation_error_does_not_trigger_native_recreate(monkeypatch):
    planned = []
    monkeypatch.setitem(sys.modules, "wx", SimpleNamespace(
        CallLater=lambda *args: planned.append(args),
    ))

    class Panel(TerminalBridgeMixin):
        _webview_pending_native = False
        _webview_legacy_edge = True
        _native_created = False
        _closed = False
        _ready = False
        _webview_failure_stage = "navigation"
        _webview_create_attempts = 1
        _webview_max_attempts = 3

        def __init__(self):
            self._webview = object()
            self._status_label = SimpleNamespace(SetLabel=lambda text: None)

        def _build_diagnostic_text(self, reason):
            return reason

    class NotNativeFailure(_Event):
        def GetString(self):
            return "File not found"

    panel = Panel()
    panel._on_error(NotNativeFailure(panel._webview))
    assert panel._webview_failure_stage == "navigation-error"
    assert planned == []


def test_legacy_native_pending_timeout_does_not_overlap_creation():
    class Panel(TerminalBridgeMixin):
        _closed = False
        _ready = False
        _webview_pending_native = False
        _webview_legacy_edge = True
        _native_created = False
        _webview_create_attempts = 1
        _webview_max_attempts = 3

        def __init__(self):
            self._webview = object()
            self._status_label = SimpleNamespace(SetLabel=lambda text: None)
            self.retries = 0

        def IsBeingDeleted(self):
            return False

        def _retry_webview_creation(self):
            self.retries += 1

    panel = Panel()
    panel._on_readiness_timeout()
    assert panel.retries == 0
    assert panel._webview_failure_stage == "bridge-timeout"


def test_legacy_loaded_event_proves_native_controller_created():
    class Panel(TerminalBridgeMixin):
        _native_created = False
        _page_loaded = False

        def _update_accessibility_label(self):
            pass

    panel = Panel()
    event = _Event(object())
    panel._on_loaded(event)
    assert panel._native_created
    assert panel._page_loaded
    assert event.skipped

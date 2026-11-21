"""Offline contracts for WebView callbacks and native parent ownership.

These tests do not claim real WebView2/wxGTK crash acceptance.
"""

from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest

from hpc_gui.wx_terminal_webview_bridge import TerminalBridgeMixin
from hpc_gui.wx_terminal_webview_lifecycle import TerminalLifecycleMixin


pytestmark = [pytest.mark.unit, pytest.mark.regression]


class _Timer:
    def __init__(self):
        self.stops = 0

    def Stop(self):
        self.stops += 1

    def IsRunning(self):
        return True


class _WebView:
    def __init__(self):
        self.stops = 0
        self.destroys = 0

    def Stop(self):
        self.stops += 1

    def Destroy(self):
        self.destroys += 1


class _NativeParent:
    def Destroy(self):
        self.parent_destroys += 1
        self.native_child.Destroy()
        return True


class _Panel(TerminalLifecycleMixin, _NativeParent):
    def __init__(self, *, pending=False):
        self.native_child = _WebView()
        self._webview = self.native_child
        self.parent_destroys = 0
        self._closed = False
        self._is_parity = True
        self._generation = 0
        self._subscriber = None
        self._subscribers_list = None
        self._retired_webviews = []
        self._readiness_timer = _Timer()
        self._resize_timer = _Timer()
        self._native_retry_timer = _Timer()
        self._native_retry_scheduled = True
        self._gtk_queue = SimpleNamespace(reset=lambda: None)
        self._gtk_screen_snapshot = None
        self._gtk_query_pending = False
        self._gtk_send_scheduled = False
        self._pending = []
        self._pending_bytes = 0
        self._pending_paste = []
        self._pending_paste_bytes = 0
        self._lang_cb = lambda *_: None
        self._webview_pending_native = pending
        self._native_created = not pending
        self._webview_legacy_edge = False
        self._fragment_ack_timer = None

    def _stop_fragment_ack_timer(self):
        pass

    def IsBeingDeleted(self):
        return False


@pytest.mark.parametrize("pending", [False, True])
def test_panel_destroy_leaves_child_destruction_to_native_parent(pending):
    panel = _Panel(pending=pending)
    retry = panel._native_retry_timer

    assert panel.Destroy() is True

    assert panel.parent_destroys == 1
    assert panel.native_child.destroys == 1
    assert panel.native_child.stops == (0 if pending else 1)
    assert retry.stops == 1
    assert panel._native_retry_timer is None
    assert panel._native_retry_scheduled is False
    assert panel._closed is True
    assert panel._generation == 1


def test_explicit_close_preserves_standalone_child_destruction():
    panel = _Panel()

    panel.close()
    panel.close()

    assert panel.native_child.stops == 1
    assert panel.native_child.destroys == 1
    assert panel.parent_destroys == 0
    assert panel._generation == 1


def test_native_parent_destroy_event_does_not_destroy_child_twice():
    panel = _Panel()
    calls = []

    class Event:
        def GetWindow(self):
            return panel

        def Skip(self):
            calls.append("skip")

    panel._on_destroy(Event())
    assert panel.native_child.destroys == 0
    assert panel._closed is True
    assert calls == ["skip"]


class _Event:
    def __init__(self, source):
        self.source = source
        self.skipped = False

    def GetEventObject(self):
        return self.source

    def Skip(self):
        self.skipped = True

    def GetString(self):
        return "Operation aborted"


def test_loaded_from_retired_webview_cannot_restore_native_state():
    class Panel(TerminalBridgeMixin):
        _closed = False
        _native_created = False
        _page_loaded = False

        def __init__(self):
            self._webview = object()
            self.a11y_calls = 0

        def _update_accessibility_label(self):
            self.a11y_calls += 1

    panel = Panel()
    stale = _Event(object())
    panel._on_loaded(stale)
    assert stale.skipped
    assert not panel._native_created
    assert not panel._page_loaded
    assert panel.a11y_calls == 0

    current = _Event(panel._webview)
    panel._on_loaded(current)
    assert current.skipped
    assert panel._native_created
    assert panel._page_loaded
    assert panel.a11y_calls == 1


@pytest.mark.parametrize("method", ["_on_loaded", "_on_error"])
def test_post_close_webview_event_does_not_update_state(method):
    class Panel(TerminalBridgeMixin):
        _closed = True
        _native_created = False
        _page_loaded = False
        _webview_failure_stage = "closed"

        def __init__(self):
            self._webview = object()

        def _update_accessibility_label(self):
            raise AssertionError("closed panel updated")

    panel = Panel()
    event = _Event(panel._webview)
    getattr(panel, method)(event)
    assert event.skipped
    assert panel._webview_failure_stage == "closed"
    assert not panel._native_created
    assert not panel._page_loaded


def test_stale_created_event_is_not_queued(monkeypatch):
    queued = []
    monkeypatch.setitem(
        sys.modules, "wx",
        SimpleNamespace(CallAfter=lambda *args: queued.append(args)),
    )

    class Panel(TerminalBridgeMixin):
        def __init__(self):
            self._closed = False
            self._webview = object()

    panel = Panel()
    stale = _Event(object())
    panel._on_native_created(stale)
    assert stale.skipped
    assert queued == []

    current = _Event(panel._webview)
    panel._on_native_created(current)
    assert current.skipped
    assert len(queued) == 1


def test_native_error_timer_can_be_cancelled_on_close(monkeypatch):
    timer = _Timer()
    monkeypatch.setitem(
        sys.modules, "wx",
        SimpleNamespace(CallLater=lambda *_args: timer),
    )

    class Panel(TerminalBridgeMixin, _Panel):
        def __init__(self):
            _Panel.__init__(self, pending=True)
            self._native_retry_scheduled = False
            self._webview_create_attempts = 1
            self._webview_max_attempts = 3
            self._native_create_errors = 0
            self._ready = False
            self._status_label = SimpleNamespace(SetLabel=lambda _s: None)

        def _build_diagnostic_text(self, reason):
            return reason

    panel = Panel()
    event = _Event(panel._webview)
    panel._on_error(event)

    assert event.skipped
    assert panel._native_retry_timer is timer
    assert panel._native_retry_scheduled
    panel.close()
    assert timer.stops == 1
    assert panel._native_retry_timer is None

"""wx shell close-handler order and failure isolation contracts."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

import hpc_gui.wx_shell_teardown as teardown


pytestmark = pytest.mark.unit


class _Frame:
    def __init__(self, events):
        self.events = events
        self._parent = None
        self.destroyed = False

    def Destroy(self):
        self.events.append("destroy")
        self.destroyed = True
        return True

    def IsBeingDeleted(self):
        return self.destroyed


class _Child:
    def __init__(self, parent, events, *, fail=False):
        self.parent = parent
        self.events = events
        self.fail = fail

    def GetParent(self):
        return self.parent

    def Close(self):
        self.events.append("child-close")
        if self.fail:
            raise RuntimeError("child failed")


class _Lifecycle:
    shutdown_started = False

    def __init__(self, events):
        self.events = events

    def set_tray_notifier(self, value):
        assert value is None
        self.events.append("tray-unregister")

    def shutdown(self):
        self.events.append("shutdown")


def _handler(
    monkeypatch, *, fail_page=False, fail_chrome=False, fail_child=False,
    pending_page=False, pending_chrome=False, allow_main_loop_exit=True,
):
    events = []
    timers = []
    frame = _Frame(events)
    frame._wx_shell_exit_main_loop_on_close = allow_main_loop_exit
    frame._wx_app = SimpleNamespace(
        ExitMainLoop=lambda: events.append("exit-main-loop"),
    )
    child = _Child(frame, events, fail=fail_child)

    def call_later(delay, callback):
        timer = SimpleNamespace(delay=delay, callback=callback)
        timers.append((delay, callback, timer))
        return timer

    wx = SimpleNamespace(
        GetTopLevelWindows=lambda: [frame, child], CallLater=call_later
    )
    lifecycle = _Lifecycle(events)
    shell_ref = [frame]

    def page_close():
        events.append("page-close")
        if fail_page:
            raise RuntimeError("page failed")
        return pending_page

    def chrome_close():
        events.append("chrome-close")
        if fail_chrome:
            raise RuntimeError("chrome failed")
        chrome_window._wx_terminal_close_pending = pending_chrome

    controls = {"files": {"page": SimpleNamespace(_wx_host_close=page_close)}}
    chrome_window = SimpleNamespace(
        Close=chrome_close, _wx_terminal_close_pending=False
    )
    chrome = [chrome_window]
    monkeypatch.setattr(teardown, "unsubscribe_language_change", lambda _: events.append("unsubscribe"))

    def save(_frame, _notebook):
        events.append("save-layout")

    close = teardown.build_shell_close_handler(
        wx, frame, object(), lifecycle, controls, chrome,
        shell_ref, object(), save,
    )
    return close, frame, lifecycle, shell_ref, chrome, events, timers


def test_close_orders_page_chrome_lifecycle_child_and_destroy(monkeypatch):
    close, frame, lifecycle, shell_ref, chrome, events, _timers = _handler(monkeypatch)

    close(None)

    assert events == [
        "save-layout", "page-close", "unsubscribe", "tray-unregister",
        "chrome-close", "shutdown", "child-close", "destroy", "exit-main-loop",
    ]
    assert shell_ref == [None]
    assert chrome == []
    assert frame._wx_shell_destroy_invoked is True
    assert frame._wx_shell_destroy_return is True


def test_close_respects_app_owned_event_loop_policy(monkeypatch):
    close, _frame, _lifecycle, _shell_ref, _chrome, events, _timers = _handler(
        monkeypatch, allow_main_loop_exit=False
    )

    close(None)

    assert events[-1] == "destroy"
    assert "exit-main-loop" not in events


def test_failed_page_and_native_close_do_not_skip_shutdown(monkeypatch):
    close, frame, _, shell_ref, chrome, events, _timers = _handler(
        monkeypatch, fail_page=True, fail_chrome=True, fail_child=True
    )

    close(None)

    assert "shutdown" in events
    assert events[-2:] == ["destroy", "exit-main-loop"]
    assert shell_ref == [None]
    assert chrome == []
    assert frame._wx_shell_destroy_return is True


def test_reentrant_close_destroys_without_repeating_cleanup(monkeypatch):
    close, frame, lifecycle, shell_ref, chrome, events, _timers = _handler(monkeypatch)
    lifecycle.shutdown_started = True

    close(None)

    assert events == ["destroy", "exit-main-loop"]
    assert shell_ref == [frame]
    assert len(chrome) == 1


def test_shutdown_started_reentrant_close_defers_pending_chrome(monkeypatch):
    close, frame, lifecycle, _shell_ref, chrome, events, timers = _handler(monkeypatch)
    lifecycle.shutdown_started = True
    chrome[0]._wx_terminal_close_pending = True

    class CloseEvent:
        vetoed = False

        def Veto(self):
            self.vetoed = True

    event = CloseEvent()
    close(event)

    assert event.vetoed is True
    assert frame._wx_shell_destroy_scheduled is True
    assert frame._wx_shell_destroy_timer is timers[0][2]
    assert "destroy" not in events
    assert len(timers) == 1
    timers[0][1]()
    assert events[-2:] == ["destroy", "exit-main-loop"]


def test_close_reentered_during_shutdown_schedules_one_destroy(monkeypatch):
    close, frame, lifecycle, _shell_ref, _chrome, events, timers = _handler(
        monkeypatch, pending_page=True
    )

    class CloseEvent:
        vetoed = False

        def Veto(self):
            self.vetoed = True

    event = CloseEvent()

    def shutdown_and_reenter():
        lifecycle.shutdown_started = True
        close(event)

    lifecycle.shutdown = shutdown_and_reenter
    close(event)

    assert event.vetoed is True
    assert frame._wx_shell_destroy_scheduled is True
    assert "destroy" not in events
    assert len(timers) == 1


@pytest.mark.parametrize("pending_owner", ["page", "chrome"])
def test_pending_native_child_defers_shell_destroy_once(monkeypatch, pending_owner):
    close, frame, _lifecycle, _shell_ref, _chrome, events, timers = _handler(
        monkeypatch,
        pending_page=pending_owner == "page",
        pending_chrome=pending_owner == "chrome",
    )

    class CloseEvent:
        def __init__(self):
            self.vetoed = False

        def Veto(self):
            self.vetoed = True

    event = CloseEvent()
    close(event)

    assert event.vetoed is True
    assert frame._wx_shell_destroy_scheduled is True
    assert "destroy" not in events
    assert len(timers) == 1
    assert timers[0][0] == 350

    close(event)
    assert events.count("destroy") == 0
    timers[0][1]()
    timers[0][1]()
    assert events[-2:] == ["destroy", "exit-main-loop"]
    assert events.count("destroy") == 1

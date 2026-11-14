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

    def Destroy(self):
        self.events.append("destroy")
        return True


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


def _handler(monkeypatch, *, fail_page=False, fail_chrome=False, fail_child=False):
    events = []
    frame = _Frame(events)
    child = _Child(frame, events, fail=fail_child)
    wx = SimpleNamespace(GetTopLevelWindows=lambda: [frame, child])
    lifecycle = _Lifecycle(events)
    shell_ref = [frame]

    def page_close():
        events.append("page-close")
        if fail_page:
            raise RuntimeError("page failed")

    def chrome_close():
        events.append("chrome-close")
        if fail_chrome:
            raise RuntimeError("chrome failed")

    controls = {"files": {"page": SimpleNamespace(_wx_host_close=page_close)}}
    chrome = [SimpleNamespace(Close=chrome_close)]
    monkeypatch.setattr(teardown, "unsubscribe_language_change", lambda _: events.append("unsubscribe"))

    def save(_frame, _notebook):
        events.append("save-layout")

    close = teardown.build_shell_close_handler(
        wx, frame, object(), lifecycle, controls, chrome,
        shell_ref, object(), save,
    )
    return close, frame, lifecycle, shell_ref, chrome, events


def test_close_orders_page_chrome_lifecycle_child_and_destroy(monkeypatch):
    close, frame, lifecycle, shell_ref, chrome, events = _handler(monkeypatch)

    close(None)

    assert events == [
        "save-layout", "page-close", "unsubscribe", "tray-unregister",
        "chrome-close", "shutdown", "child-close", "destroy",
    ]
    assert shell_ref == [None]
    assert chrome == []
    assert frame._wx_shell_destroy_invoked is True
    assert frame._wx_shell_destroy_return is True


def test_failed_page_and_native_close_do_not_skip_shutdown(monkeypatch):
    close, frame, _, shell_ref, chrome, events = _handler(
        monkeypatch, fail_page=True, fail_chrome=True, fail_child=True
    )

    close(None)

    assert "shutdown" in events
    assert events[-1] == "destroy"
    assert shell_ref == [None]
    assert chrome == []
    assert frame._wx_shell_destroy_return is True


def test_reentrant_close_destroys_without_repeating_cleanup(monkeypatch):
    close, frame, lifecycle, shell_ref, chrome, events = _handler(monkeypatch)
    lifecycle.shutdown_started = True

    close(None)

    assert events == ["destroy"]
    assert shell_ref == [frame]
    assert len(chrome) == 1

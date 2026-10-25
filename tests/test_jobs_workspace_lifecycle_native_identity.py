"""Native wx wrapper identity checks for Jobs workspace teardown."""

from threading import RLock
from types import SimpleNamespace
from unittest.mock import Mock

from hpc_gui.jobs import workspace_lifecycle as lifecycle_module


class _WindowWrapper:
    def __init__(self, handle):
        self.handle = handle

    def GetHandle(self):
        return self.handle


def _controller(host):
    browser = SimpleNamespace(_wx_host_close=Mock())
    timer = SimpleNamespace(Stop=Mock())
    state = {
        "closed": False,
        "files_browser_closed": False,
        "outputs_pending_generations": set(),
        "followers": {},
    }
    controller = lifecycle_module.JobsWorkspaceLifecycle.__new__(
        lifecycle_module.JobsWorkspaceLifecycle
    )
    controller.bindings = SimpleNamespace(
        host=host,
        state=state,
        state_lock=RLock(),
        files_browser=browser,
        timer=timer,
        refresh_labels=lambda: None,
    )
    return controller, state, browser, timer


def test_destroy_matches_a_distinct_wrapper_for_same_native_window(monkeypatch):
    monkeypatch.setattr(lifecycle_module, "unsubscribe_language_change", lambda _cb: None)
    controller, state, browser, timer = _controller(_WindowWrapper(123))
    event = SimpleNamespace(GetEventObject=lambda: _WindowWrapper(123), Skip=Mock())

    controller.on_destroy(event)

    assert state["closed"] is True
    assert state["files_browser_closed"] is True
    browser._wx_host_close.assert_called_once_with()
    timer.Stop.assert_called_once_with()
    event.Skip.assert_called_once_with()


def test_destroy_ignores_a_different_native_window(monkeypatch):
    monkeypatch.setattr(lifecycle_module, "unsubscribe_language_change", lambda _cb: None)
    controller, state, browser, timer = _controller(_WindowWrapper(123))
    event = SimpleNamespace(GetEventObject=lambda: _WindowWrapper(456), Skip=Mock())

    controller.on_destroy(event)

    assert state["closed"] is False
    assert state["files_browser_closed"] is False
    browser._wx_host_close.assert_not_called()
    timer.Stop.assert_not_called()
    event.Skip.assert_called_once_with()

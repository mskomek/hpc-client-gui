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
    timer = SimpleNamespace(Stop=Mock(), SetOwner=Mock())
    state = {
        "closed": False,
        "files_browser_closed": False,
        "outputs_pending_generations": set(),
        "followers": {},
    }
    controller = lifecycle_module.JobsWorkspaceLifecycle.__new__(
        lifecycle_module.JobsWorkspaceLifecycle
    )
    controller._host_id = getattr(host, "handle", None)
    controller.bindings = SimpleNamespace(
        wx=SimpleNamespace(EVT_TIMER=object()),
        host=host,
        state=state,
        state_lock=RLock(),
        files_browser=browser,
        timer=timer,
        refresh_labels=lambda: None,
    )
    return controller, state, browser, timer


def test_close_unbinds_timer_before_destroy(monkeypatch):
    monkeypatch.setattr(lifecycle_module, "unsubscribe_language_change", lambda _cb: None)
    host = SimpleNamespace(Hide=Mock(), Destroy=Mock(), Unbind=Mock())
    controller, state, _browser, timer = _controller(host)
    controller.bindings.embedded = False
    controller.bindings.actions = SimpleNamespace()
    order = []
    timer.Stop.side_effect = lambda: order.append("stop")
    timer.SetOwner.side_effect = lambda owner: order.append(f"owner:{owner}")
    host.Unbind.side_effect = lambda *_args, **_kwargs: order.append("unbind")
    host.Destroy.side_effect = lambda: order.append("destroy")

    controller.close()

    timer.Stop.assert_called_once_with()
    host.Unbind.assert_called_once_with(
        controller.bindings.wx.EVT_TIMER,
        handler=controller.tick,
        source=timer,
    )
    host.Destroy.assert_called_once_with()
    assert state["closed"] is True
    timer.SetOwner.assert_called_once_with(None)
    assert order == ["stop", "unbind", "owner:None", "destroy"]


def test_close_finishes_when_timer_wrapper_is_already_deleted(monkeypatch):
    monkeypatch.setattr(lifecycle_module, "unsubscribe_language_change", lambda _cb: None)
    host = SimpleNamespace(Hide=Mock(), Destroy=Mock(), Unbind=Mock())
    controller, _state, _browser, timer = _controller(host)
    controller.bindings.embedded = False
    controller.bindings.actions = SimpleNamespace()
    timer.Stop.side_effect = RuntimeError("deleted native timer")

    controller.close()

    host.Unbind.assert_called_once()
    host.Destroy.assert_called_once_with()
    timer.SetOwner.assert_called_once_with(None)


def test_queued_tick_after_close_is_ignored():
    controller, state, _browser, _timer = _controller(_WindowWrapper(123))
    state["closed"] = True
    event = Mock()

    controller.tick(event)

    event.Skip.assert_not_called()


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


def test_destroy_uses_cached_id_after_native_wrapper_is_invalid(monkeypatch):
    monkeypatch.setattr(lifecycle_module, "unsubscribe_language_change", lambda _cb: None)
    controller, state, browser, timer = _controller(_WindowWrapper(123))

    def deleted_handle():
        raise RuntimeError("destroyed wx wrapper")

    event = SimpleNamespace(
        GetEventObject=lambda: SimpleNamespace(GetHandle=deleted_handle),
        GetId=lambda: 123,
        Skip=Mock(),
    )

    controller.on_destroy(event)

    assert state["closed"] is True
    assert state["files_browser_closed"] is True
    browser._wx_host_close.assert_called_once_with()
    timer.Stop.assert_called_once_with()
    event.Skip.assert_called_once_with()

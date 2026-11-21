"""Production wx event-loop ownership after real frame destruction."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from hpc_gui.wx_application import install_main_frame_exit_policy


pytestmark = [pytest.mark.unit, pytest.mark.regression]


class _Frame:
    def __init__(self):
        self.handlers = {}
        self._wx_shell_exit_loop_error_type = None

    def Bind(self, event_type, callback):
        self.handlers[event_type] = callback

    def GetId(self):
        return 713


class _NativeTopLevelAlias:
    def __init__(self, *, window_id=713, parent=None, fail_parent=False):
        self.window_id = window_id
        self.parent = parent
        self.fail_parent = fail_parent

    def GetId(self):
        return self.window_id

    def GetParent(self):
        if self.fail_parent:
            raise RuntimeError("wrapped C/C++ parent was deleted")
        return self.parent


class _Event:
    def __init__(self, window, *, fail_window=False, fail_skip=False):
        self.window = window
        self.fail_window = fail_window
        self.fail_skip = fail_skip
        self.skip_count = 0

    def GetWindow(self):
        if self.fail_window:
            raise RuntimeError("native wrapper already deleted")
        return self.window

    def Skip(self):
        self.skip_count += 1
        if self.fail_skip:
            raise RuntimeError("window deleted during event")


def _setup(call_after=None):
    queued = []
    policies = []
    exited = []
    event_key = object()
    wx = SimpleNamespace(
        EVT_WINDOW_DESTROY=event_key,
        CallAfter=call_after or (lambda callback: queued.append(callback)),
        TopLevelWindow=_NativeTopLevelAlias,
    )
    app = SimpleNamespace(
        SetExitOnFrameDelete=lambda value: policies.append(value),
        ExitMainLoop=lambda: exited.append("exit"),
    )
    frame = _Frame()
    install_main_frame_exit_policy(wx, app, frame)
    return frame, event_key, queued, policies, exited


def test_exit_queued_once_only_after_real_main_frame_destroy():
    frame, key, queued, policies, exited = _setup()
    handler = frame.handlers[key]
    child_event = _Event(object())
    handler(child_event)

    assert child_event.skip_count == 1
    assert queued == []
    assert policies == [True]

    actual = _Event(frame)
    handler(actual)
    handler(actual)

    assert actual.skip_count == 2
    assert len(queued) == 1
    assert exited == []
    queued[0]()
    assert exited == ["exit"]


def test_destroy_event_with_dead_wrapper_is_safe_and_skipped():
    frame, key, queued, _policies, exited = _setup()
    event = _Event(frame, fail_window=True, fail_skip=True)

    frame.handlers[key](event)

    assert queued == []
    assert exited == []
    assert event.skip_count == 1


def test_failed_queue_is_recorded_and_a_second_event_can_retry():
    calls = []
    queued = []

    def call_after(callback):
        calls.append(True)
        if len(calls) == 1:
            raise RuntimeError("event loop unavailable")
        queued.append(callback)

    frame, key, _ignored, policies, exited = _setup(call_after=call_after)
    callback = frame.handlers[key]

    callback(_Event(frame))
    assert frame._wx_shell_exit_loop_error_type == "RuntimeError"
    callback(_Event(frame))
    assert len(queued) == 1
    assert policies == [True]
    assert exited == []
    queued[0]()
    assert exited == ["exit"]


def test_gtk_native_top_level_alias_is_accepted_without_cpp_equality():
    frame, key, queued, policies, exited = _setup()
    actual_alias = _NativeTopLevelAlias(window_id=frame.GetId(), parent=None)

    frame.handlers[key](_Event(actual_alias))
    frame.handlers[key](_Event(actual_alias))

    assert policies == [True]
    assert len(queued) == 1
    queued[0]()
    assert exited == ["exit"]


def test_gtk_child_and_other_top_level_destroy_are_ignored():
    frame, key, queued, policies, exited = _setup()
    handler = frame.handlers[key]

    class _ChildWithCollidingId:
        def GetId(self):
            return frame.GetId()

        def GetParent(self):
            return None

    # Even an accidentally colliding child ID cannot match the main frame.
    handler(_Event(_ChildWithCollidingId()))
    # An owned top-level dialog is not the unparented application main frame.
    handler(_Event(_NativeTopLevelAlias(window_id=frame.GetId(), parent=frame)))
    # A different top-level frame with no parent must not end this app.
    handler(_Event(_NativeTopLevelAlias(window_id=99, parent=None)))

    assert queued == []
    assert exited == []
    assert policies == [True]


def test_gtk_alias_with_deleted_native_parent_lookup_still_exits():
    frame, key, queued, policies, exited = _setup()
    alias = _NativeTopLevelAlias(
        window_id=frame.GetId(),
        fail_parent=True,
    )

    frame.handlers[key](_Event(alias))

    assert policies == [True]
    assert len(queued) == 1
    queued[0]()
    assert exited == ["exit"]

"""Native window identity helpers shared by wx Jobs window lifecycles."""

from __future__ import annotations

from typing import Any


def same_wx_window(left: Any, right: Any) -> bool:
    """Compare wx wrappers by native handle when wrapper identity differs."""
    if left is right:
        return True
    try:
        left_handle = left.GetHandle()
        right_handle = right.GetHandle()
        if left_handle is not None and right_handle is not None:
            return left_handle == right_handle
    except Exception:
        pass
    try:
        return bool(left == right)
    except Exception:
        return False


def matches_wx_destroy_event(event: Any, window: Any, window_id: int | None) -> bool:
    """Match a destroy event after wx has invalidated a window wrapper."""
    try:
        event_window = event.GetEventObject()
    except (AttributeError, RuntimeError):
        event_window = None
    if event_window is not None and same_wx_window(event_window, window):
        return True
    if window_id is None:
        return False
    try:
        return event.GetId() == window_id
    except (AttributeError, RuntimeError):
        return False

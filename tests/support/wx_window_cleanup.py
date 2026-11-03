"""Deterministic teardown for native wx regression tests."""

from __future__ import annotations

import time
from typing import Any


_ACTIVE_JOB_REQUESTS = (
    "in_flight",
    "sacct_in_flight",
    "details_in_flight",
    "status_in_flight",
    "outputs_in_flight",
    "cancel_in_flight",
)


def _job_workspace_idle(window: Any) -> bool:
    state = getattr(window, "_wx_jobs_state", None)
    if not isinstance(state, dict):
        return True
    if any(state.get(key) for key in _ACTIVE_JOB_REQUESTS):
        return False
    if any(state.get(key, 0) for key in ("sacct_requests", "details_requests", "outputs_requests")):
        return False
    if state.get("outputs_active_generations"):
        return False
    return not any(
        getattr(follower, "state", None) is not None
        and getattr(follower.state, "in_flight", False)
        for follower in state.get("followers", {}).values()
    )


def _pump_events(wx: Any, app: Any) -> None:
    try:
        app.ProcessPendingEvents()
    except Exception:
        pass
    try:
        wx.YieldIfNeeded()
    except Exception:
        pass


def cleanup_wx_windows(wx: Any, app: Any, existing_ids: set[int], timeout: float = 5.0) -> None:
    """Drain callbacks, close newly created frames through their real lifecycle, and reap them."""
    windows = [
        window for window in wx.GetTopLevelWindows()
        if window and window.GetId() not in existing_ids
    ]
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline and any(not _job_workspace_idle(window) for window in windows):
        _pump_events(wx, app)
        wx.MilliSleep(10)

    for window in windows:
        try:
            if not window.IsBeingDeleted():
                window.Close(force=True)
        except Exception:
            try:
                window.Destroy()
            except Exception:
                pass

    for _ in range(20):
        _pump_events(wx, app)
        remaining_ids = {
            window.GetId() for window in wx.GetTopLevelWindows()
            if window and window.GetId() not in existing_ids
        }
        if not remaining_ids:
            break
        wx.MilliSleep(10)

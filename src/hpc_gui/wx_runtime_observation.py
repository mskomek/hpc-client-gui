"""Canonical evidence derivation for packaged wx runtime observations."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


def _pair(value: Any) -> tuple[int, int] | None:
    if not isinstance(value, (tuple, list)) or len(value) < 2:
        return None
    try:
        return int(value[0]), int(value[1])
    except (TypeError, ValueError):
        return None


def finalize_runtime_observation(
    runtime: dict[str, Any], *,
    pty_initial_requested: Any,
    pty_initial_observed: Any,
    pty_resize_requested: Any,
    pty_resize_observed: Any,
    transport_closed: bool,
    cleanup_callbacks_drained: bool,
    frame_destroyed: bool,
    event_loop_exited: bool,
    exit_code: int | None,
    timed_out: bool,
    mandatory_checks: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """Merge child lifecycle facts and parent transport/process readbacks.

    Explicit child FAIL values remain failures. PENDING values are finalized
    only from authoritative parent observations after process termination.
    """
    finalized = deepcopy(runtime)
    checks = finalized.setdefault("checks", {})
    checks.setdefault("process_started", "PASS")
    observation = finalized.setdefault("observation", {})
    initial_requested = _pair(pty_initial_requested)
    initial_observed = _pair(pty_initial_observed)
    resize_requested = _pair(pty_resize_requested)
    resize_observed = _pair(pty_resize_observed)
    pty_verified = (
        initial_requested == (96, 31)
        and initial_observed == (96, 31)
        and resize_requested == (123, 45)
        and resize_observed == (123, 45)
    )
    observation.update({
        "pty_initial_requested": initial_requested,
        "pty_initial_observed": initial_observed,
        "pty_resize_requested": resize_requested,
        "pty_resize_observed": resize_observed,
        "pty_resize_verified": pty_verified,
        "transport_closed": bool(transport_closed),
        "cleanup_callbacks_drained": bool(cleanup_callbacks_drained),
        "frame_destroyed": bool(frame_destroyed),
        "event_loop_exited": bool(event_loop_exited),
        "child_exit_code": exit_code,
        "child_timed_out": bool(timed_out),
    })
    if checks.get("pty_resize") != "FAIL":
        checks["pty_resize"] = "PASS" if pty_verified else "FAIL"
    shutdown_verified = (
        transport_closed
        and cleanup_callbacks_drained
        and frame_destroyed
        and event_loop_exited
        and exit_code == 0
        and not timed_out
    )
    if checks.get("clean_shutdown") != "FAIL":
        checks["clean_shutdown"] = "PASS" if shutdown_verified else "FAIL"
    required = mandatory_checks or tuple(checks)
    finalized["result"] = "PASS" if required and all(
        checks.get(name) == "PASS" for name in required
    ) else "FAIL"
    finalized["finalized_by"] = "parent-transport-and-process-observer/1"
    return finalized

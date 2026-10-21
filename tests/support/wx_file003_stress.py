"""Shared measurements for the serial GUI-FILE-003 stress campaign."""

from __future__ import annotations

from collections import Counter


METRICS = Counter()
EXECUTED: dict[str, tuple[int, int]] = {}
ZERO_INVARIANTS = (
    "wrong_targets",
    "stale_ui_overwrites",
    "destroyed_control_callbacks",
    "leaked_file_workers",
    "leaked_wx_windows",
    "duplicate_transfers",
    "lost_transfers",
    "leaked_transfer_sessions",
    "mixed_session_transfer_operations",
)


def _record(name: str, executed: int, required: int) -> None:
    EXECUTED[name] = (executed, required)
    assert executed >= required, f"{name}: executed {executed}, required {required}"

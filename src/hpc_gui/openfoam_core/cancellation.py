"""Cooperative cancellation contract for bounded case scans."""

from __future__ import annotations

from typing import Any


class ScanCancelledError(RuntimeError):
    """Raised between file operations when a lint scan is cancelled."""


def raise_if_cancelled(cancel_event: Any = None) -> None:
    """Stop at the next safe boundary when an optional event is set."""
    if cancel_event is not None and cancel_event.is_set():
        raise ScanCancelledError("OpenFOAM lint was cancelled")

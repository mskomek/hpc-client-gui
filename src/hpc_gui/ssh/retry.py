"""Bounded retry policy for establishing SSH sessions."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


def retry_connection(
    operation: Callable[[], T],
    *,
    attempts: int,
    on_retry: Callable[[str], None],
    non_retryable: tuple[type[BaseException], ...] = (),
    delay_seconds: float = 1.0,
) -> T:
    """Retry a failed connection operation a bounded number of times."""
    limit = max(1, min(5, int(attempts)))
    for attempt in range(1, limit + 1):
        try:
            return operation()
        except Exception as exc:
            if attempt >= limit or isinstance(exc, non_retryable):
                raise
            on_retry(
                f"SSH: connection attempt {attempt}/{limit} failed; "
                f"retrying in {delay_seconds:g} second(s) ({type(exc).__name__})"
            )
            time.sleep(delay_seconds)
    raise RuntimeError("unreachable SSH retry state")

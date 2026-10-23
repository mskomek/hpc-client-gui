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


def retry_ssh_connection(operation: Callable[[], T], *, on_retry: Callable[[str], None]) -> T:
    """Apply SSH settings and avoid retries for deterministic auth/policy errors."""
    from hpc_gui.config.storage import get_ssh_connection_attempts
    from hpc_gui.ssh.host_keys import HostKeyChangedError, HostKeyRejectedError
    from hpc_gui.ssh.jump import JumpAuthenticationError, JumpForwardingDeniedError

    return retry_connection(
        operation,
        attempts=get_ssh_connection_attempts(),
        on_retry=on_retry,
        non_retryable=(
            HostKeyChangedError,
            HostKeyRejectedError,
            JumpAuthenticationError,
            JumpForwardingDeniedError,
        ),
    )

"""Thread-safe state for the optional startup update check."""

from __future__ import annotations

from threading import Lock
from typing import Any


class StartupUpdateState:
    """Accept one worker result unless this session skipped or timed out."""

    CHECKING = "checking"
    COMPLETE = "complete"
    SKIPPED = "skipped"
    TIMED_OUT = "timed_out"

    def __init__(self) -> None:
        self._lock = Lock()
        self._status = self.CHECKING
        self._release: Any = None
        self._error: Exception | None = None

    @property
    def status(self) -> str:
        with self._lock:
            return self._status

    def complete(self, release: Any = None, error: Exception | None = None) -> bool:
        """Record a worker result only while the check is still current."""
        with self._lock:
            if self._status != self.CHECKING:
                return False
            self._release = release
            self._error = error
            self._status = self.COMPLETE
            return True

    def skip(self) -> bool:
        """Skip once; a completed or timed-out check cannot be skipped."""
        with self._lock:
            if self._status != self.CHECKING:
                return False
            self._status = self.SKIPPED
            return True

    def timeout(self) -> bool:
        """Close the check at its deadline and fence off late worker results."""
        with self._lock:
            if self._status != self.CHECKING:
                return False
            self._status = self.TIMED_OUT
            return True

    def result(self) -> tuple[Any, Exception | None]:
        """Return a result only after normal completion."""
        with self._lock:
            if self._status != self.COMPLETE:
                return None, None
            return self._release, self._error

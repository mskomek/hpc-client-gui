"""Framework-neutral Jobs refresh state machine for W28.

Owns HPC-W07-REFRESH-001..004::

    idle -> refreshing -> success(timestamp) | failure(error, prior-data-marked-stale)

A transient failure never silently clears useful prior data. When prior rows
remain visible after a failure they are flagged stale. Overlapping refreshes
carry a monotonic sequence; an older response can never overwrite a newer one.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class JobsRefreshState:
    """Small testable refresh lifecycle owned by the Jobs workspace."""

    status: str = "idle"
    sequence: int = 0
    applied_sequence: int = 0
    last_success_ts: str = ""
    last_error: str = ""
    stale: bool = False
    data: list[Any] = field(default_factory=list)

    # -- lifecycle ------------------------------------------------------

    def begin(self) -> int:
        """Enter ``refreshing`` and issue the next monotonic sequence."""
        self.sequence += 1
        self.status = "refreshing"
        return self.sequence

    def is_current(self, seq: int) -> bool:
        """True when ``seq`` is the latest issued refresh."""
        return int(seq) == int(self.sequence)

    def should_apply(self, seq: int) -> bool:
        """Older responses must not overwrite newer context."""
        return int(seq) == int(self.sequence) and int(seq) > int(self.applied_sequence)

    def complete_success(self, seq: int, rows: Any, *, timestamp: str | None = None) -> bool:
        """Apply ``rows`` when ``seq`` is still the newest refresh.

        Returns True when applied, False when discarded as stale/overlapped.
        """
        if not self.should_apply(seq):
            return False
        self.data = list(rows or [])
        self.applied_sequence = int(seq)
        self.status = "success"
        self.last_success_ts = timestamp if timestamp is not None else _utcnow_iso()
        self.last_error = ""
        self.stale = False
        return True

    def complete_failure(self, seq: int, error: Any, *, clear_on_failure: bool = False) -> bool:
        """Record ``error`` without silently clearing prior data.

        By default prior rows are retained and flagged stale so the UI can
        mark them visibly stale instead of implying a fresh success. Pass
        ``clear_on_failure=True`` only when the UX explicitly intends to drop
        the old list.
        """
        if not self.should_apply(seq):
            return False
        self.applied_sequence = int(seq)
        self.status = "failure"
        self.last_error = str(error or "refresh failed").strip() or "refresh failed"
        if clear_on_failure:
            self.data = []
            self.stale = False
        else:
            self.stale = bool(self.data)
        return True

    # -- readback ---------------------------------------------------------

    def status_text(self) -> str:
        """Human-visible refresh status; stale prior data is explicit."""
        if self.status == "refreshing":
            return "refreshing"
        if self.status == "success":
            base = f"updated {self.last_success_ts}" if self.last_success_ts else "updated"
            return base
        if self.status == "failure":
            if self.data and not self.stale:
                return f"refresh failed: {self.last_error}"
            if self.stale:
                return f"stale since {self.last_success_ts or 'last success'}: {self.last_error}"
            return f"refresh failed: {self.last_error}"
        return "idle"

    def snapshot(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "sequence": self.sequence,
            "applied_sequence": self.applied_sequence,
            "last_success_ts": self.last_success_ts,
            "last_error": self.last_error,
            "stale": self.stale,
            "row_count": len(self.data),
        }

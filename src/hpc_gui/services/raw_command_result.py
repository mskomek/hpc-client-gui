"""Framework-neutral raw command result model for the Raw Viewer fallback."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class RawCommandResult:
    """Immutable snapshot of a raw scheduler/provider command response.

    This model is the trusted backend adapter output that feeds both:
    - the Raw Viewer (direct display)
    - the current parser (parsed UI)

    Making parser success a prerequisite for raw access is explicitly avoided.
    """

    source_id: str = ""
    command: str = ""
    stdout: str = ""
    stderr: str = ""
    exit_code: int = -1
    timestamp: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_response(
        cls,
        *,
        source_id: str = "",
        command: str = "",
        stdout: str = "",
        stderr: str = "",
        exit_code: int = -1,
        metadata: dict[str, Any] | None = None,
    ) -> RawCommandResult:
        """Create a RawCommandResult with an auto-generated ISO timestamp."""
        return cls(
            source_id=source_id,
            command=command,
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            timestamp=datetime.now(timezone.utc).isoformat(),
            metadata=metadata or {},
        )

    @property
    def has_error(self) -> bool:
        return self.exit_code > 0

    @property
    def display_command(self) -> str:
        """Safe command string for display (never executed by the viewer)."""
        return self.command or f"[{self.source_id}]"

"""Framework-neutral cluster server status model for Wave 79.

Only includes fields justified by actual TRUBA lssrv output.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ClusterServerStatus:
    """Normalized model for one cluster server entry from lssrv output."""

    name: str
    state: str = ""
    total_cpus: str = ""
    free_cpus: str = ""
    queue: str = ""
    raw_row: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

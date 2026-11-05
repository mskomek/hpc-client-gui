"""Runtime availability gating (W65 CAT-003, G05).

Never executes a solver during discovery. ``probe`` only inspects PATH
metadata; ``--help`` capture requires explicit opt-in and a disposable
target, and is recorded as such.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass


@dataclass(frozen=True)
class Availability:
    tool: str
    found: bool
    path: str | None
    help_captured: bool
    status: str  # ACTIVE-TYPED | RAW-ADVANCED | UNAVAILABLE | UNSUPPORTED


def probe(tool: str, declared: str, *, help_captured: bool = False) -> Availability:
    if declared == "UNSUPPORTED":
        return Availability(tool, False, None, False, "UNSUPPORTED")
    path = shutil.which(tool)
    if path is None:
        return Availability(tool, False, None, False, "UNAVAILABLE")
    if declared == "RAW-ADVANCED":
        return Availability(tool, True, path, help_captured, "RAW-ADVANCED")
    return Availability(tool, True, path, help_captured, "ACTIVE-TYPED")


def gate_or_disable(tool: str, declared: str) -> dict:
    avail = probe(tool, declared)
    return {"tool": tool, "status": avail.status, "path": avail.path,
            "enabled": avail.status in ("ACTIVE-TYPED", "RAW-ADVANCED"),
            "reason": "" if avail.found else "binary not found on PATH; action disabled"}

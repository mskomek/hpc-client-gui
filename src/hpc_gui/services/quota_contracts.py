"""Value contracts shared by quota adapters and the quota runtime."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class QuotaResult:
    state: str
    used_bytes: int | None = None
    soft_limit_bytes: int | None = None
    hard_limit_bytes: int | None = None
    scope: str = "unknown"
    pool_id: str | None = None
    error: str | None = None
    used_files: int | None = None
    soft_limit_files: int | None = None
    hard_limit_files: int | None = None
    storage_id: str | None = None
    path: str | None = None

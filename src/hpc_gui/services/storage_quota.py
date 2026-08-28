"""Provider-neutral storage/quota models.

This module deliberately performs no SSH or filesystem work. Providers are
registered by the application only after their read-only request and parser
have been reviewed.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Protocol

STORAGE_KINDS = frozenset({"home", "scratch", "project", "custom"})
QUOTA_SCOPES = frozenset({"user", "group", "project"})
SOURCE_STATUSES = frozenset({"ok", "unsupported", "unknown", "stale", "error"})


def _nonnegative(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("quota values must be non-negative integers or null")
    return value


@dataclass(frozen=True)
class StorageArea:
    id: str
    label: str
    kind: str
    path_template: str
    quota_scope: str
    quota_pool_id: str
    provider_id: str
    provider_options: Mapping[str, Any]
    documentation_url: str = ""
    policy_summary: str = ""

    def __post_init__(self) -> None:
        if not self.id or not self.label or not self.path_template:
            raise ValueError("storage area id, label, and path_template are required")
        if self.kind not in STORAGE_KINDS:
            raise ValueError(f"unsupported storage kind: {self.kind}")
        if self.quota_scope not in QUOTA_SCOPES:
            raise ValueError(f"unsupported quota scope: {self.quota_scope}")
        if not self.quota_pool_id or not self.provider_id:
            raise ValueError("quota pool and provider IDs are required")
        if not isinstance(self.provider_options, Mapping):
            raise ValueError("provider_options must be an object")


@dataclass(frozen=True)
class QuotaResult:
    area_id: str
    quota_pool_id: str
    scope: str
    scope_identity: str | None = None
    used_bytes: int | None = None
    soft_limit_bytes: int | None = None
    hard_limit_bytes: int | None = None
    file_count: int | None = None
    soft_file_limit: int | None = None
    hard_file_limit: int | None = None
    grace_state: str | None = None
    measured_at: datetime | None = None
    freshness: str = "unknown"
    source_status: str = "unknown"
    error: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.source_status not in SOURCE_STATUSES:
            raise ValueError(f"unsupported quota source status: {self.source_status}")
        if self.scope not in QUOTA_SCOPES:
            raise ValueError(f"unsupported quota scope: {self.scope}")
        for field in (
            "used_bytes", "soft_limit_bytes", "hard_limit_bytes",
            "file_count", "soft_file_limit", "hard_file_limit",
        ):
            _nonnegative(getattr(self, field))


class QuotaProvider(Protocol):
    provider_id: str

    def measure(self, area: StorageArea, *, scope_identity: str) -> QuotaResult:
        """Perform one reviewed, read-only measurement."""


class QuotaProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, QuotaProvider] = {}

    def register(self, provider: QuotaProvider) -> None:
        provider_id = getattr(provider, "provider_id", "")
        if not isinstance(provider_id, str) or not provider_id.strip():
            raise ValueError("provider_id is required")
        if provider_id in self._providers:
            raise ValueError(f"quota provider already registered: {provider_id}")
        self._providers[provider_id] = provider

    def get(self, provider_id: str) -> QuotaProvider | None:
        return self._providers.get(provider_id)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)

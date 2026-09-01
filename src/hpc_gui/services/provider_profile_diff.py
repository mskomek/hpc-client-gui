"""Semantic diffs for declarative provider snapshots."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class ProviderChange:
    section: str
    detail: str


@dataclass(frozen=True)
class ProviderProfileDiff:
    provider_id: str
    from_version: str
    to_version: str
    changes: tuple[ProviderChange, ...]
    last_verified: str = ""

    @property
    def changed(self) -> bool:
        return bool(self.changes)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    def summary(self) -> list[str]:
        return [f"{change.section}: {change.detail}" for change in self.changes]


def _value(profile: Any, key: str, default: Any = None) -> Any:
    if isinstance(profile, Mapping):
        return profile.get(key, default)
    return getattr(profile, key, default)


def _semantic(profile: Any, section: str) -> Any:
    if section == "auth":
        access = _value(profile, "access", {}) or {}
        return tuple(access.get("auth_methods", ())) if isinstance(access, Mapping) else ()
    if section == "partitions":
        hints = _value(profile, "scheduler_hints", {}) or {}
        return tuple(hints.get("partitions", ())) if isinstance(hints, Mapping) else ()
    if section == "requirements":
        return _value(profile, "requirements", {}) or {}
    if section == "storage":
        areas = _value(profile, "storage", ()) or ()
        return tuple(
            (
                str(area.get("id", "")),
                str(area.get("kind", "custom")),
                bool(area.get("enabled", True)),
                str(area.get("path_template", "")),
            )
            for area in areas if isinstance(area, Mapping)
        )
    if section == "quota":
        sources = _value(profile, "quota_sources", ()) or ()
        return tuple(
            (str(source.get("id", "")), str(source.get("backend_id", "")), bool(source.get("enabled", False)))
            for source in sources if isinstance(source, Mapping)
        )
    if section == "docs":
        metadata = _value(profile, "metadata", {}) or {}
        if not isinstance(metadata, Mapping):
            return ()
        return (str(metadata.get("documentation_url", "")), tuple(metadata.get("source_refs", ())))
    return None


def _detail(section: str, before: Any, after: Any) -> str:
    if section == "auth":
        return f"authentication methods {list(before)} → {list(after)}"
    if section == "partitions":
        return f"partitions {list(before)} → {list(after)}"
    if section == "requirements":
        old = sorted(before) if isinstance(before, Mapping) else []
        new = sorted(after) if isinstance(after, Mapping) else []
        return f"required fields {old} → {new}"
    if section == "storage":
        return f"storage areas {len(before)} → {len(after)}"
    if section == "quota":
        return f"quota sources {len(before)} → {len(after)}"
    return "documentation references changed"


def build_provider_profile_diff(
    before: Any,
    after: Any,
    *,
    from_version: str = "",
    to_version: str = "",
) -> ProviderProfileDiff:
    """Compare only support-relevant provider fields; never emit raw JSON."""
    changes = tuple(
        ProviderChange(section, _detail(section, old, new))
        for section in ("auth", "partitions", "requirements", "storage", "quota", "docs")
        if (old := _semantic(before, section)) != (new := _semantic(after, section))
    )
    provider_id = str(_value(after, "profile_id", "") or _value(before, "profile_id", ""))
    metadata = _value(after, "metadata", {}) or {}
    verified = str(metadata.get("last_verified", "")) if isinstance(metadata, Mapping) else ""
    return ProviderProfileDiff(provider_id, from_version, to_version, changes, verified)


def apply_provider_to_connection(
    connection: Mapping[str, Any], provider: Mapping[str, Any], *, confirmed: bool = False
) -> dict[str, Any]:
    """Return a connection snapshot; update it only after explicit confirmation."""
    result = dict(connection)
    if confirmed:
        result["provider_template"] = dict(provider)
    return result

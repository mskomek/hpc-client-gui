"""Safe, side-effect-free quota eligibility gate."""

from __future__ import annotations

from typing import Any, Iterable


def quota_gate(
    source: dict[str, Any] | None,
    *,
    backend_ids: Iterable[str] = (),
    consented: bool | None = None,
    connected: bool = False,
    subject_available: bool = True,
) -> str:
    """Return quota state without creating timers, transports, or processes."""
    if not isinstance(source, dict) or not str(source.get("command_template") or "").strip():
        return "not_configured"
    if source.get("enabled") is not True:
        return "disabled"
    backend_id = str(source.get("backend_id") or "").strip()
    if not backend_id or backend_id not in set(backend_ids) or not subject_available:
        return "incomplete/unsupported"
    if "\n" in str(source["command_template"]) or "\r" in str(source["command_template"]):
        return "invalid_configuration"
    if consented is None:
        consented = source.get("consent") is True
    if not consented:
        return "ready_not_enabled"
    return "eligible" if connected else "ready_not_enabled"


def quota_state_for_profile(
    profile: dict[str, Any] | None,
    *,
    backend_ids: Iterable[str] = (),
    connected: bool = False,
) -> str:
    """Evaluate the first stored provider quota source without side effects."""
    template = profile.get("provider_template") if isinstance(profile, dict) else None
    sources = template.get("quota_sources") if isinstance(template, dict) else None
    source = sources[0] if isinstance(sources, list) and sources and isinstance(sources[0], dict) else None
    return quota_gate(source, backend_ids=backend_ids, connected=connected)

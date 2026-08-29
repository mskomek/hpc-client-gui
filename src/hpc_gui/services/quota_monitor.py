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

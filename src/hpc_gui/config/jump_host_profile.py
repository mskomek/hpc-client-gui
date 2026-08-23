"""Profile-scoped jump-host (bastion) settings.

Pure helpers; no filesystem I/O, no network, no Qt.
"""

from __future__ import annotations

from typing import Any


JUMP_HOST_DEFAULTS: dict[str, Any] = {
    "enabled": False,
    "host": "",
    "port": 22,
    "username": "",
    "key_path": "",
    "host_key_policy": "accept-new",
}

_JUMP_POLICIES = {"accept-new", "strict"}


def _coerce_port(value: object) -> int:
    try:
        port = int(value)  # type: ignore[arg-type]
    except (OverflowError, TypeError, ValueError):
        return 22
    return port if 1 <= port <= 65535 else 22


def normalize_jump_host_settings(value: object) -> dict[str, Any]:
    """Return normalized jump-host settings for any input value."""
    settings = dict(JUMP_HOST_DEFAULTS)
    if not isinstance(value, dict):
        return settings
    enabled = value.get("enabled")
    if isinstance(enabled, bool):
        settings["enabled"] = enabled
    for key in ("host", "username", "key_path"):
        candidate = value.get(key)
        if isinstance(candidate, str):
            settings[key] = candidate.strip()
    settings["port"] = _coerce_port(value.get("port"))
    policy = str(value.get("host_key_policy") or "").strip()
    settings["host_key_policy"] = policy if policy in _JUMP_POLICIES else "accept-new"
    return settings


def patch_jump_host_settings(
    existing_value: object,
    patch: dict[str, Any],
) -> dict[str, Any]:
    """Patch supplied keys onto existing jump-host settings.

    Keeps unknown nested keys so future extensions survive an edit;
    normalizes known fields; never inserts runtime objects.
    """
    base: dict[str, Any] = (
        dict(existing_value) if isinstance(existing_value, dict) else {}
    )
    known = normalize_jump_host_settings({**base, **(patch or {})})
    return {**base, **known}

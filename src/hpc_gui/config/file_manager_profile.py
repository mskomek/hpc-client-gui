"""Profile-scoped file-manager settings.

Pure helpers; no filesystem I/O and no Qt. Unknown nested keys are
preserved so later file-manager features cannot be lost by an edit.
"""

from __future__ import annotations

from typing import Any

from hpc_gui.config.storage import (
    load_profiles,
    merge_profile_patch,
    upsert_profile,
)


FILE_MANAGER_DEFAULTS: dict[str, Any] = {
    "local_start_dir": "",
    "comparison_enabled": False,
}

SYNC_DEFAULTS: dict[str, Any] = {
    "enabled": False,
    "local_root": "",
    "remote_root": "",
}


def _normalize_sync(value: object) -> dict[str, Any]:
    result = dict(SYNC_DEFAULTS)
    if not isinstance(value, dict):
        return result
    enabled = value.get("enabled")
    if isinstance(enabled, bool):
        result["enabled"] = enabled
    for key in ("local_root", "remote_root"):
        candidate = value.get(key)
        if isinstance(candidate, str):
            result[key] = candidate.strip()
    return result


def normalize_file_manager_settings(value: object) -> dict[str, Any]:
    """Return normalized file-manager settings for any input value."""
    settings = dict(FILE_MANAGER_DEFAULTS)
    settings["sync"] = _normalize_sync(
        value.get("sync") if isinstance(value, dict) else None
    )
    if not isinstance(value, dict):
        return settings
    local_start_dir = value.get("local_start_dir")
    settings["local_start_dir"] = (
        str(local_start_dir).strip() if isinstance(local_start_dir, str) else ""
    )
    comparison_enabled = value.get("comparison_enabled")
    settings["comparison_enabled"] = bool(comparison_enabled)
    settings["sync"] = _normalize_sync(value.get("sync"))
    return settings


def patch_file_manager_settings(
    existing_value: object,
    patch: dict[str, Any],
) -> dict[str, Any]:
    """Patch supplied keys onto existing file-manager settings.

    Starts from the existing dict when valid (keeping unknown nested
    keys), applies only supplied patch keys, normalizes known fields,
    and never inserts transient runtime objects. A partial ``sync``
    patch keeps the stored sibling fields of ``sync``.
    """
    base: dict[str, Any] = (
        dict(existing_value) if isinstance(existing_value, dict) else {}
    )
    incoming = dict(patch or {})
    if "sync" in incoming and isinstance(base.get("sync"), dict) and isinstance(
        incoming["sync"], dict
    ):
        incoming["sync"] = {**base["sync"], **incoming["sync"]}
    known = normalize_file_manager_settings({**base, **incoming})
    return {**base, **known}


def update_profile_file_manager_settings(
    profile_name: str,
    patch: dict[str, Any],
) -> dict[str, Any]:
    """Patch file-manager settings on a stored profile and persist it.

    Uses the FM-01 merge path, so the stable ID, encrypted passwords,
    plugin provenance, system settings, jump state, and unknown keys all
    survive. Returns the updated file-manager dictionary.
    """
    name = str(profile_name or "").strip()
    if not name:
        raise ValueError("profile name is required")
    profile = next(
        (item for item in load_profiles() if item.get("name") == name),
        None,
    )
    if profile is None:
        raise KeyError(name)
    updated = patch_file_manager_settings(profile.get("file_manager"), patch)
    merged = merge_profile_patch(profile, {"file_manager": updated})
    upsert_profile(merged)
    return updated

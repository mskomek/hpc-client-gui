from __future__ import annotations

import uuid
from typing import Any, Dict, Iterable, List, Optional

from hpc_gui.config.settings_store import _coerce_int_in_range
from hpc_gui.config.storage_io import (
    _backup_before_migration,
    _config_path,
    load_config,
    save_config,
)


def merge_profile_patch(
    existing: dict[str, Any] | None,
    patch: dict[str, Any],
    *,
    remove_keys: Iterable[str] = (),
) -> dict[str, Any]:
    """Patch known profile fields onto an existing profile record.

    The result starts from a shallow copy of ``existing`` so unknown
    top-level keys and untouched nested dictionaries survive an edit.
    Only explicitly listed keys are removed. Pure function; no I/O.
    """
    result: dict[str, Any] = dict(existing) if isinstance(existing, dict) else {}
    for key, value in (patch or {}).items():
        result[key] = value
    for key in remove_keys or ():
        result.pop(key, None)
    return result


def resolve_provider_overrides(
    provider: dict[str, Any] | None,
    overrides: dict[str, Any] | None,
) -> dict[str, Any]:
    """Apply explicit provider overrides with inherit/set/clear semantics.

    Missing keys inherit. ``None`` and blank strings persist a clear, while
    false-y non-string values such as ``False`` remain deliberate settings.
    """
    result = dict(provider) if isinstance(provider, dict) else {}
    for key, value in (overrides or {}).items():
        result[key] = None if value is None or (isinstance(value, str) and not value.strip()) else value
    return result


def coerce_profile_transfer_parallelism(value: Any, default: int = 1) -> int:
    return _coerce_int_in_range(value, default, 1, 10)


def _is_valid_parallelism(value: Any) -> bool:
    """Strict validity for stored profile values (no bools/strings)."""
    return (
        isinstance(value, int)
        and not isinstance(value, bool)
        and 1 <= value <= 10
    )


def migrate_legacy_transfer_parallelism(cfg: Dict[str, Any]) -> bool:
    """One-time migration of the legacy global transfer-parallelism setting.

    v1.4.0 made the per-profile ``transfer_parallelism`` the single source of
    truth, so profiles saved earlier silently fell back to 1. This copies a
    valid legacy global value into every profile that lacks a valid profile-
    specific one. It runs once per profile (the written field makes later
    runs no-ops), never overwrites valid profile-specific values, clamps to
    1..10, and preserves all other fields.

    Pure function over the config mapping; returns True when it changed it.
    """
    profiles = cfg.get("profiles")
    if not isinstance(profiles, list):
        return False
    settings = cfg.get("settings")
    legacy_raw = settings.get("transfer_parallelism") if isinstance(settings, dict) else None
    # Numeric legacy values are clamped into the supported range; anything
    # else is malformed and contributes the safe default.
    if isinstance(legacy_raw, int) and not isinstance(legacy_raw, bool):
        legacy_value = _coerce_int_in_range(legacy_raw, 1, 1, 10)
    else:
        legacy_value = 1
    changed = False
    for profile in profiles:
        if not isinstance(profile, dict):
            continue
        current = profile.get("transfer_parallelism")
        if _is_valid_parallelism(current):
            continue  # profile-specific choice always wins
        target = coerce_profile_transfer_parallelism(legacy_value, 1)
        if current != target:
            profile["transfer_parallelism"] = target
            changed = True
    return changed


def coerce_profile_ssh_timeout(value: Any, default: float | None = None) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if number <= 0:
        return default
    return min(600.0, number)


_CONFLICT_ACTIONS = {"overwrite", "overwrite_if_newer", "resume", "skip", "rename", "cancel"}


def get_profile_conflict_action(profile_name: str) -> str | None:
    name = str(profile_name or "").strip()
    if not name:
        return None
    profile = next((item for item in load_profiles() if item.get("name") == name), None)
    action = str((profile or {}).get("conflict_action", "")).strip()
    return action if action in _CONFLICT_ACTIONS else None


def set_profile_conflict_action(profile_name: str, action: str) -> str:
    name = str(profile_name or "").strip()
    value = str(action or "").strip()
    if not name or value not in _CONFLICT_ACTIONS:
        return ""
    profiles = load_profiles()
    for profile in profiles:
        if profile.get("name") == name:
            profile["conflict_action"] = value
            upsert_profile(profile)
            return value
    return ""


def clear_profile_conflict_action(profile_name: str) -> None:
    name = str(profile_name or "").strip()
    if not name:
        return
    profile = next((item for item in load_profiles() if item.get("name") == name), None)
    if profile is not None and "conflict_action" in profile:
        profile = dict(profile)
        profile.pop("conflict_action", None)
        upsert_profile(profile)


def load_profiles() -> List[Dict[str, Any]]:
    cfg = load_config()
    profs = cfg.get("profiles", [])
    if not isinstance(profs, list):
        return []
    changed = False
    # Profiles used to be identified by name alone, which loses everything
    # keyed to a profile as soon as the user renames it.  Stamp a stable id on
    # legacy entries once, on first read.
    missing = [p for p in profs if isinstance(p, dict) and not p.get("id")]
    if missing:
        for profile in missing:
            profile["id"] = str(uuid.uuid4())
        changed = True
    # One-time migration: copy the legacy global transfer-parallelism value
    # into profiles that lack a valid profile-specific one.
    if migrate_legacy_transfer_parallelism(cfg):
        changed = True
    if changed:
        cfg["profiles"] = profs
        _backup_before_migration(_config_path())
        save_config(cfg)
    return profs


def get_profile_id(name: str) -> Optional[str]:
    """Return the stable id of the named profile, if it exists."""
    clean = (name or "").strip()
    profile = next((p for p in load_profiles() if p.get("name") == clean), None)
    return str(profile.get("id")) if profile and profile.get("id") else None


def upsert_profile(profile: Dict[str, Any]) -> None:
    """Insert or update by profile['id'], falling back to profile['name']."""
    name = (profile.get("name") or "").strip()
    if not name:
        raise ValueError("profile name is required")

    cfg = load_config()
    profs = cfg.get("profiles", [])
    if not isinstance(profs, list):
        profs = []

    profile_id = str(profile.get("id") or "").strip()
    idx = None
    if profile_id:
        # Match on id first so a rename keeps everything bound to this profile.
        idx = next((i for i, p in enumerate(profs) if p.get("id") == profile_id), None)
    if idx is None:
        idx = next((i for i, p in enumerate(profs) if p.get("name") == name), None)
    if not profile_id:
        profile_id = str((profs[idx].get("id") if idx is not None else "") or uuid.uuid4())
    profile = dict(profile, id=profile_id)

    if idx is None:
        profs.append(profile)
    else:
        profs[idx] = profile

    cfg["profiles"] = profs
    cfg["last_profile"] = name
    cfg["last_profile_id"] = profile_id
    save_config(cfg)


def delete_profile(name: str) -> None:
    name = (name or "").strip()
    cfg = load_config()
    profs = cfg.get("profiles", [])
    if not isinstance(profs, list):
        profs = []
    removed = [p for p in profs if p.get("name") == name]
    cfg["profiles"] = [p for p in profs if p.get("name") != name]
    if cfg.get("last_profile") == name:
        cfg.pop("last_profile", None)
        cfg.pop("last_profile_id", None)
    save_config(cfg)
    for profile in removed:
        reference = profile.get("password_keychain_ref")
        still_used = any(
            reference and p.get("password_keychain_ref") == reference
            for p in cfg["profiles"]
        )
        if reference and not still_used:
            from ..core.secret_store import delete_keychain_secret

            delete_keychain_secret(str(reference))
        profile_id = str(profile.get("id") or "")
        if not profile_id:
            continue
        # Deleting a profile must take its private state with it, otherwise
        # remote paths outlive the profile they belong to.
        from ..services.remote_navigation_store import delete_profile_navigation

        delete_profile_navigation(profile_id)


def get_last_profile_name() -> Optional[str]:
    cfg = load_config()
    v = cfg.get("last_profile")
    return v if isinstance(v, str) and v.strip() else None

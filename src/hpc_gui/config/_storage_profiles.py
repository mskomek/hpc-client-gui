from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from hpc_gui.config._storage_core import (
    _backup_before_migration, _config_path, load_config, save_config,
    migrate_legacy_transfer_parallelism,
)

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

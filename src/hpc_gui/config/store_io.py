from __future__ import annotations

import json
import os
import shutil
import tempfile
import uuid
from pathlib import Path

from typing import Any, Dict, List, Optional


def _config_path() -> Path:
    # Resolve through the storage facade so monkeypatching storage._config_dir
    # (the long-standing test seam) keeps working after the split.
    from . import storage

    return storage._config_path()


def _next_config_backup(path: Path) -> Path:
    backup = path.with_name(path.name + ".bak")
    index = 1
    while backup.exists():
        backup = path.with_name(f"{path.name}.bak.{index}")
        index += 1
    return backup


def _backup_corrupt_config(path: Path) -> None:
    path.replace(_next_config_backup(path))


def _backup_before_migration(path: Path) -> None:
    """Keep a rollback copy before a migration replaces valid user data."""
    if path.exists():
        shutil.copy2(path, _next_config_backup(path))


def load_config() -> Dict[str, Any]:
    p = _config_path()
    if not p.exists():
        return {"profiles": [], "settings": {}}
    try:
        loaded = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise ValueError("config root must be a JSON object")
        if not isinstance(loaded.get("profiles", []), list):
            raise ValueError("config profiles must be a JSON array")
        if not isinstance(loaded.get("settings", {}), dict):
            raise ValueError("config settings must be a JSON object")
        return loaded
    except Exception:
        # corrupted config; keep a backup and start fresh
        try:
            _backup_corrupt_config(p)
        except Exception:
            pass
        return {"profiles": [], "settings": {}}


def load_settings() -> Dict[str, Any]:
    """Load application-wide settings stored in config.json.

    Settings are kept separate from profiles.
    """
    cfg = load_config()
    st = cfg.get("settings", {})
    return st if isinstance(st, dict) else {}


def update_settings(patch: Dict[str, Any]) -> Dict[str, Any]:
    """Merge patch into settings and persist."""
    cfg = load_config()
    st = cfg.get("settings")
    if not isinstance(st, dict):
        st = {}
    for k, v in (patch or {}).items():
        st[k] = v
    cfg["settings"] = st
    _persist(cfg)
    return st


def _coerce_positive_int(value: Any, default: int) -> int:
    try:
        coerced = int(value)
    except Exception:
        return default
    return coerced if coerced > 0 else default


def _coerce_int_in_range(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        coerced = int(value)
    except Exception:
        return default
    if coerced < minimum:
        return minimum
    if coerced > maximum:
        return maximum
    return coerced


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


def _persist(cfg: Dict[str, Any]) -> None:
    # Resolve through the storage facade so monkeypatching storage.save_config
    # (the long-standing test seam) keeps working after the split.
    from . import storage

    storage.save_config(cfg)


def save_config(cfg: Dict[str, Any]) -> None:
    p = _config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    if os.name == "posix":
        p.parent.chmod(0o700)
    fd, tmp_name = tempfile.mkstemp(
        prefix=p.name + ".", suffix=".tmp", dir=p.parent
    )
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(cfg, ensure_ascii=False, indent=2))
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, p)
        if os.name == "posix":
            p.chmod(0o600)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


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
        _persist(cfg)
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
    _persist(cfg)


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
    _persist(cfg)
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

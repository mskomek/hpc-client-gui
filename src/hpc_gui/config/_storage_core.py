from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable

from hpc_gui.core.paths import app_data_dir

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

def _config_dir() -> Path:
    return app_data_dir()

def _config_path() -> Path:
    return _config_dir() / "config.json"

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

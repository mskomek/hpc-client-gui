from __future__ import annotations

import json
import os
import tempfile
import uuid
from pathlib import Path

from hpc_gui.core.paths import app_data_dir
from typing import Any, Dict, Iterable, List, Optional


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


def _config_dir() -> Path:
    return app_data_dir()


def _config_path() -> Path:
    return _config_dir() / "config.json"


def load_config() -> Dict[str, Any]:
    p = _config_path()
    if not p.exists():
        return {"profiles": [], "settings": {}}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        # corrupted config; keep a backup and start fresh
        try:
            p.rename(p.with_suffix(".json.bak"))
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
    save_config(cfg)
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


def get_jobs_outputs_refresh_interval_seconds(default: int = 15) -> int:
    """Return the live Jobs & Outputs polling interval in seconds."""
    st = load_settings()
    return _coerce_positive_int(st.get("jobs_outputs_refresh_interval_seconds", default), default)


def get_live_tracking_warning_interval_seconds(default: int = 60) -> int:
    """Return idle live-follow warning interval; zero disables the warning."""
    return _coerce_int_in_range(load_settings().get("live_tracking_warning_interval_seconds", default), default, 0, 3600)

def set_live_tracking_warning_interval_seconds(seconds: int) -> int:
    value = _coerce_int_in_range(seconds, 60, 0, 3600)
    update_settings({"live_tracking_warning_interval_seconds": value})
    return value

def get_pause_live_follow_when_minimized_enabled(default: bool = True) -> bool:
    """Return whether minimized windows should pause live output following."""
    value = load_settings().get("pause_live_follow_when_minimized_enabled", default)
    return value if isinstance(value, bool) else default


def get_follow_window_open_minimized_enabled(default: bool = True) -> bool:
    """Return whether new independent follow windows should open minimized."""
    value = load_settings().get("follow_window_open_minimized_enabled", default)
    return value if isinstance(value, bool) else default


def set_jobs_outputs_refresh_interval_seconds(seconds: int) -> int:
    """Persist the live Jobs & Outputs polling interval in seconds."""
    value = _coerce_positive_int(seconds, 15)
    update_settings({"jobs_outputs_refresh_interval_seconds": value})
    return value


def get_squeue_auto_refresh_enabled(default: bool = True) -> bool:
    """Return whether squeue should refresh with the Jobs polling timer."""
    value = load_settings().get("squeue_auto_refresh_enabled", default)
    return value if isinstance(value, bool) else default


def get_sacct_auto_refresh_enabled(default: bool = True) -> bool:
    """Return whether sacct should refresh with the Jobs polling timer."""
    value = load_settings().get("sacct_auto_refresh_enabled", default)
    return value if isinstance(value, bool) else default


def get_lssrv_auto_refresh_enabled(default: bool = False) -> bool:
    """Return whether lssrv should refresh with the Jobs polling timer."""
    value = load_settings().get("lssrv_auto_refresh_enabled", default)
    return value if isinstance(value, bool) else default


def set_lssrv_auto_refresh_enabled(enabled: bool) -> bool:
    """Persist whether lssrv should refresh with the Jobs polling timer."""
    value = bool(enabled)
    update_settings({"lssrv_auto_refresh_enabled": value})
    return value


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
def get_transfer_parallelism(default: int = 1) -> int:
    """Return the configured transfer queue parallelism, capped at 10."""
    st = load_settings()
    return _coerce_int_in_range(st.get("transfer_parallelism", default), default, 1, 10)


def set_transfer_parallelism(count: int) -> int:
    """Persist the transfer queue parallelism, capped at 10."""
    value = _coerce_int_in_range(count, 1, 1, 10)
    update_settings({"transfer_parallelism": value})
    return value


def get_remote_directory_cache_enabled(default: bool = True) -> bool:
    """Return whether recently visited remote directories should be cached."""
    value = load_settings().get("remote_directory_cache_enabled", default)
    return value if isinstance(value, bool) else default


def set_remote_directory_cache_enabled(enabled: bool) -> bool:
    """Persist the remote directory cache preference."""
    value = bool(enabled)
    update_settings({"remote_directory_cache_enabled": value})
    return value


_TRANSFER_COMPLETION_ACTIONS = {
    "none",
    "notification",
    "attention",
    "play_sound",
    "close_once",
    "run_command",
    "close",
    "reboot_once",
    "shutdown_once",
    "suspend_once",
}


def get_transfer_completion_action(default: str = "none") -> str:
    """Return the saved, non-destructive transfer-completion preference."""
    value = str(load_settings().get("transfer_completion_action", default)).strip()
    return value if value in _TRANSFER_COMPLETION_ACTIONS else default


def set_transfer_completion_action(action: str) -> str:
    """Persist a completion preference; callers decide whether it is safe to run."""
    value = str(action or "").strip()
    if value not in _TRANSFER_COMPLETION_ACTIONS:
        value = "none"
    update_settings({"transfer_completion_action": value})
    return value


def get_upload_preflight_confirmation_enabled(default: bool = True) -> bool:
    """Return whether local uploads should show the preflight confirmation."""
    value = load_settings().get("upload_preflight_confirmation_enabled", default)
    return value if isinstance(value, bool) else default


def set_upload_preflight_confirmation_enabled(enabled: bool) -> bool:
    """Persist whether local uploads should show the preflight confirmation."""
    value = bool(enabled)
    update_settings({"upload_preflight_confirmation_enabled": value})
    return value


def get_transfer_checksum_verification_enabled(default: bool = False) -> bool:
    """Return whether completed transfers should be verified with SHA-256."""
    value = load_settings().get("transfer_checksum_verification_enabled", default)
    return value if isinstance(value, bool) else default


def set_transfer_checksum_verification_enabled(enabled: bool) -> bool:
    """Persist the optional post-transfer SHA-256 verification setting."""
    value = bool(enabled)
    update_settings({"transfer_checksum_verification_enabled": value})
    return value


SBATCH_FOLLOW_MODE_NONE = "none"
SBATCH_FOLLOW_MODE_OUTPUTS_TAB = "outputs_tab"
SBATCH_FOLLOW_MODE_NEW_TABS_SPLIT = "new_tabs_split"
SBATCH_FOLLOW_MODE_NEW_WINDOW_COMBINED = "new_window_combined"
SBATCH_FOLLOW_MODE_NEW_WINDOWS_SPLIT = "new_windows_split"
SBATCH_FOLLOW_MODES = {
    SBATCH_FOLLOW_MODE_NONE,
    SBATCH_FOLLOW_MODE_OUTPUTS_TAB,
    SBATCH_FOLLOW_MODE_NEW_TABS_SPLIT,
    SBATCH_FOLLOW_MODE_NEW_WINDOW_COMBINED,
    SBATCH_FOLLOW_MODE_NEW_WINDOWS_SPLIT,
}


def get_sbatch_follow_mode(default: str = SBATCH_FOLLOW_MODE_OUTPUTS_TAB) -> str:
    """Return the persisted post-sbatch output/error follow destination.

    The temporary boolean preference introduced in 1.1.10 is read as a
    migration source only: ``False`` means stay on the current screen and
    ``True`` means the original Outputs-tab behaviour.  Missing or malformed
    settings preserve the historical default of opening the Outputs tab.
    """
    settings = load_settings()
    value = str(settings.get("sbatch_follow_mode", "")).strip()
    if value in SBATCH_FOLLOW_MODES:
        return value
    legacy_value = settings.get("focus_jobs_outputs_after_submission_enabled")
    if isinstance(legacy_value, bool):
        return (
            SBATCH_FOLLOW_MODE_OUTPUTS_TAB
            if legacy_value
            else SBATCH_FOLLOW_MODE_NONE
        )
    return default if default in SBATCH_FOLLOW_MODES else SBATCH_FOLLOW_MODE_OUTPUTS_TAB


def set_sbatch_follow_mode(mode: str) -> str:
    """Persist a validated post-sbatch output/error follow destination."""
    value = str(mode or "").strip()
    if value not in SBATCH_FOLLOW_MODES:
        value = SBATCH_FOLLOW_MODE_OUTPUTS_TAB
    update_settings({"sbatch_follow_mode": value})
    return value


def get_last_seen_changelog_version(default: str = "") -> str:
    """Return the app version whose startup changelog was last acknowledged."""
    value = load_settings().get("last_seen_changelog_version", default)
    return str(value or "").strip()


def set_last_seen_changelog_version(version: str) -> str:
    """Persist that the startup changelog has been shown for a version."""
    value = str(version or "").strip()
    update_settings({"last_seen_changelog_version": value})
    return value


def get_cli_external_access_enabled(default: bool = False) -> bool:
    """Return whether remote CLI commands may run without a GUI session."""
    value = load_settings().get("cli_external_access_enabled", default)
    return value if isinstance(value, bool) else default


def set_cli_external_access_enabled(enabled: bool) -> bool:
    """Persist whether remote CLI commands may run without a GUI session."""
    value = bool(enabled)
    update_settings({"cli_external_access_enabled": value})
    return value


def get_cli_default_profile(default: str = "") -> str:
    """Return the saved CLI default profile name, or an empty string."""
    value = load_settings().get("cli_default_profile", default)
    return str(value or "").strip()


def set_cli_default_profile(name: str) -> str:
    """Persist the CLI default profile name."""
    value = str(name or "").strip()
    update_settings({"cli_default_profile": value})
    return value


def get_ftp_transfer_type(default: str = "auto") -> str:
    value = str(load_settings().get("ftp_transfer_type", default)).strip().lower()
    return value if value in {"auto", "binary", "ascii"} else default


def set_ftp_transfer_type(value: str) -> str:
    normalized = str(value or "").strip().lower()
    if normalized not in {"auto", "binary", "ascii"}:
        normalized = "auto"
    update_settings({"ftp_transfer_type": normalized})
    return normalized


def _normalize_file_extension(extension: str) -> str:
    value = str(extension or "").strip().lower()
    if not value:
        return ""
    return value if value.startswith(".") else f".{value}"


def get_file_associations() -> Dict[str, str]:
    value = load_settings().get("file_associations", {})
    if not isinstance(value, dict):
        return {}
    associations: Dict[str, str] = {}
    for extension, program in value.items():
        normalized = _normalize_file_extension(str(extension))
        program_path = str(program or "").strip()
        if normalized and program_path:
            associations[normalized] = program_path
    return associations


def get_file_association(extension: str) -> str:
    normalized = _normalize_file_extension(extension)
    if not normalized:
        return ""
    return get_file_associations().get(normalized, "")


def set_file_association(extension: str, program_path: str) -> Dict[str, str]:
    normalized = _normalize_file_extension(extension)
    associations = get_file_associations()
    if normalized:
        program = str(program_path or "").strip()
        if program:
            associations[normalized] = program
        else:
            associations.pop(normalized, None)
    update_settings({"file_associations": associations})
    return associations


def clear_file_association(extension: str) -> Dict[str, str]:
    normalized = _normalize_file_extension(extension)
    associations = get_file_associations()
    if normalized:
        associations.pop(normalized, None)
    update_settings({"file_associations": associations})
    return associations


def get_ftp_state() -> Dict[str, Any]:
    st = load_settings()
    sizes = st.get("ftp_splitter_sizes", [1, 1])
    if not isinstance(sizes, list) or len(sizes) != 2:
        sizes = [1, 1]
    try:
        sizes = [max(1, int(sizes[0])), max(1, int(sizes[1]))]
    except Exception:
        sizes = [1, 1]
    active = str(st.get("ftp_active_remote", "scratch")).lower()
    if active not in {"scratch", "home"}:
        active = "scratch"
    return {
        "local_dir": str(st.get("ftp_local_dir", "")),
        "active_remote": active,
        "splitter_sizes": sizes,
    }


def update_ftp_state(
    *,
    local_dir: str | None = None,
    active_remote: str | None = None,
    splitter_sizes: List[int] | None = None,
) -> Dict[str, Any]:
    patch: Dict[str, Any] = {}
    if local_dir is not None:
        patch["ftp_local_dir"] = str(local_dir)
    if active_remote is not None:
        active = str(active_remote).lower()
        patch["ftp_active_remote"] = active if active in {"scratch", "home"} else "scratch"
    if splitter_sizes is not None and len(splitter_sizes) == 2:
        patch["ftp_splitter_sizes"] = [max(1, int(value)) for value in splitter_sizes]
    return update_settings(patch)


def save_config(cfg: Dict[str, Any]) -> None:
    p = _config_path()
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


def get_ui_pref_bool(key: str, default: bool = True) -> bool:
    cfg = load_config()
    ui = cfg.get("ui", {})
    if not isinstance(ui, dict):
        ui = {}
    v = ui.get(key)
    if isinstance(v, bool):
        return v
    return default


def set_ui_pref_bool(key: str, value: bool) -> None:
    cfg = load_config()
    ui = cfg.get("ui", {})
    if not isinstance(ui, dict):
        ui = {}
    ui[key] = bool(value)
    cfg["ui"] = ui
    save_config(cfg)

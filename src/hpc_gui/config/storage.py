from __future__ import annotations


from pathlib import Path

from hpc_gui.core.paths import app_data_dir
from typing import Any, Dict, Iterable, Optional


from .store_io import (_next_config_backup as _next_config_backup,
                       _backup_corrupt_config as _backup_corrupt_config,
                       _backup_before_migration as _backup_before_migration,
                       load_config as load_config, load_settings as load_settings,
                       update_settings as update_settings, save_config as save_config,
                       load_profiles as load_profiles, get_profile_id as get_profile_id,
                       upsert_profile as upsert_profile, delete_profile as delete_profile,
                       get_last_profile_name as get_last_profile_name,
                       migrate_legacy_transfer_parallelism as migrate_legacy_transfer_parallelism,
                       _is_valid_parallelism as _is_valid_parallelism,
                       coerce_profile_transfer_parallelism as coerce_profile_transfer_parallelism,
                       coerce_profile_ssh_timeout as coerce_profile_ssh_timeout,
                       _coerce_positive_int as _coerce_positive_int,
                       _coerce_int_in_range as _coerce_int_in_range)
from .storage_settings import (get_jobs_outputs_refresh_interval_seconds as get_jobs_outputs_refresh_interval_seconds,
                               get_live_tracking_warning_interval_seconds as get_live_tracking_warning_interval_seconds,
                               set_live_tracking_warning_interval_seconds as set_live_tracking_warning_interval_seconds,
                               get_pause_live_follow_when_minimized_enabled as get_pause_live_follow_when_minimized_enabled,
                               get_follow_window_open_minimized_enabled as get_follow_window_open_minimized_enabled,
                               set_jobs_outputs_refresh_interval_seconds as set_jobs_outputs_refresh_interval_seconds,
                               get_squeue_auto_refresh_enabled as get_squeue_auto_refresh_enabled,
                               get_sacct_auto_refresh_enabled as get_sacct_auto_refresh_enabled,
                               get_lssrv_auto_refresh_enabled as get_lssrv_auto_refresh_enabled,
                               set_lssrv_auto_refresh_enabled as set_lssrv_auto_refresh_enabled,
                               get_hide_finished_jobs_enabled as get_hide_finished_jobs_enabled,
                               set_hide_finished_jobs_enabled as set_hide_finished_jobs_enabled,
                               get_profile_conflict_action as get_profile_conflict_action,
                               set_profile_conflict_action as set_profile_conflict_action,
                               clear_profile_conflict_action as clear_profile_conflict_action,
                               get_transfer_parallelism as get_transfer_parallelism,
                               set_transfer_parallelism as set_transfer_parallelism,
                               get_remote_directory_cache_enabled as get_remote_directory_cache_enabled,
                               set_remote_directory_cache_enabled as set_remote_directory_cache_enabled,
                               get_transfer_completion_action as get_transfer_completion_action,
                               set_transfer_completion_action as set_transfer_completion_action,
                               get_upload_preflight_confirmation_enabled as get_upload_preflight_confirmation_enabled,
                               set_upload_preflight_confirmation_enabled as set_upload_preflight_confirmation_enabled,
                               get_transfer_checksum_verification_enabled as get_transfer_checksum_verification_enabled,
                               set_transfer_checksum_verification_enabled as set_transfer_checksum_verification_enabled,
                               get_sbatch_follow_mode as get_sbatch_follow_mode,
                               set_sbatch_follow_mode as set_sbatch_follow_mode,
                               get_last_seen_changelog_version as get_last_seen_changelog_version,
                               set_last_seen_changelog_version as set_last_seen_changelog_version,
                               get_cli_external_access_enabled as get_cli_external_access_enabled,
                               set_cli_external_access_enabled as set_cli_external_access_enabled,
                               get_ssh_connection_attempts as get_ssh_connection_attempts,
                               set_ssh_connection_attempts as set_ssh_connection_attempts,
                               get_cli_default_profile as get_cli_default_profile,
                               set_cli_default_profile as set_cli_default_profile,
                               get_ftp_transfer_type as get_ftp_transfer_type,
                               set_ftp_transfer_type as set_ftp_transfer_type,
                               _normalize_file_extension as _normalize_file_extension,
                               get_file_associations as get_file_associations,
                               get_file_association as get_file_association,
                               set_file_association as set_file_association,
                               clear_file_association as clear_file_association,
                               get_ftp_state as get_ftp_state,
                               update_ftp_state as update_ftp_state,
                               _CONFLICT_ACTIONS as _CONFLICT_ACTIONS,
                               _TRANSFER_COMPLETION_ACTIONS as _TRANSFER_COMPLETION_ACTIONS,
                               SBATCH_FOLLOW_MODE_NONE as SBATCH_FOLLOW_MODE_NONE,
                               SBATCH_FOLLOW_MODE_OUTPUTS_TAB as SBATCH_FOLLOW_MODE_OUTPUTS_TAB,
                               SBATCH_FOLLOW_MODE_NEW_TABS_SPLIT as SBATCH_FOLLOW_MODE_NEW_TABS_SPLIT,
                               SBATCH_FOLLOW_MODE_NEW_WINDOW_COMBINED as SBATCH_FOLLOW_MODE_NEW_WINDOW_COMBINED,
                               SBATCH_FOLLOW_MODE_NEW_WINDOWS_SPLIT as SBATCH_FOLLOW_MODE_NEW_WINDOWS_SPLIT,
                               SBATCH_FOLLOW_MODES as SBATCH_FOLLOW_MODES)


def _config_dir() -> Path:
    return app_data_dir()


def _config_path() -> Path:
    return _config_dir() / 'config.json'

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


MAIN_WINDOW_STATE_KEY = "main_window"


def get_main_window_state() -> Optional[Dict[str, Any]]:
    """Return the raw persisted wx main-window record, or ``None``.

    ``None`` covers absent state (fresh defaults), corrupt records (wrong
    types, non-positive sizes, non-dict ``ui`` section) and foreign blobs
    such as legacy Qt geometry payloads, which never drive wx geometry
    (HPC-W09-UISTATE-015). Never raises for malformed user data.
    """
    try:
        cfg = load_config()
    except Exception:
        return None
    ui = cfg.get("ui", {})
    if not isinstance(ui, dict):
        return None
    raw = ui.get(MAIN_WINDOW_STATE_KEY)
    if not isinstance(raw, dict):
        return None
    try:
        x = int(raw["x"])
        y = int(raw["y"])
        width = int(raw["width"])
        height = int(raw["height"])
    except (KeyError, TypeError, ValueError):
        return None
    if width <= 0 or height <= 0:
        return None
    selected = raw.get("selected_tab", None)
    if selected is not None:
        try:
            selected = int(selected)
        except (TypeError, ValueError):
            selected = None
    return {
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "maximized": bool(raw.get("maximized", False)),
        "selected_tab": selected,
    }


def save_main_window_state(
    *,
    x: int,
    y: int,
    width: int,
    height: int,
    maximized: bool = False,
    selected_tab: Optional[int] = None,
) -> Dict[str, Any]:
    """Persist the wx main-window layout record (HPC-W09-UISTATE-009..014).

    Raises ``ValueError`` for non-positive sizes or non-integer geometry so
    corrupt values can never be written; the shutdown hook treats this as
    best-effort and keeps the previous record on failure.
    """
    width = int(width)
    height = int(height)
    if width <= 0 or height <= 0:
        raise ValueError(f"Refusing to persist non-positive window size {(width, height)}")
    record: Dict[str, Any] = {
        "x": int(x),
        "y": int(y),
        "width": width,
        "height": height,
        "maximized": bool(maximized),
    }
    if selected_tab is not None:
        record["selected_tab"] = int(selected_tab)
    cfg = load_config()
    ui = cfg.get("ui", {})
    if not isinstance(ui, dict):
        ui = {}
    ui[MAIN_WINDOW_STATE_KEY] = record
    cfg["ui"] = ui
    save_config(cfg)
    return record


def clear_main_window_state() -> None:
    """Remove the persisted wx main-window record (fresh-defaults path)."""
    try:
        cfg = load_config()
    except Exception:
        return
    ui = cfg.get("ui", {})
    if not isinstance(ui, dict):
        return
    if MAIN_WINDOW_STATE_KEY in ui:
        del ui[MAIN_WINDOW_STATE_KEY]
        cfg["ui"] = ui
        try:
            save_config(cfg)
        except Exception:
            pass

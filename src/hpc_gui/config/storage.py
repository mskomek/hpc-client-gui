"""Stable public facade for application configuration persistence."""
from __future__ import annotations

from functools import wraps
from pathlib import Path
from typing import Any, Callable

from hpc_gui.config import storage_io as _storage_io
from hpc_gui.config import settings_compat as _settings_compat
from hpc_gui.config.storage_io import (
    load_config as _load_config_impl,
    load_settings,
    update_settings,
    _backup_before_migration as _backup_before_migration,
    _backup_corrupt_config as _backup_corrupt_config,
    _config_dir as _ORIGINAL_CONFIG_DIR,
    _config_path as _ORIGINAL_CONFIG_PATH,
    _next_config_backup as _next_config_backup,
)

from hpc_gui.config.profiles_store import (
    clear_profile_conflict_action,
    coerce_profile_ssh_timeout,
    coerce_profile_transfer_parallelism,
    delete_profile,
    get_last_profile_name,
    get_profile_conflict_action,
    get_profile_id,
    load_profiles,
    merge_profile_patch,
    migrate_legacy_transfer_parallelism,
    resolve_provider_overrides,
    set_profile_conflict_action,
    upsert_profile,
    _CONFLICT_ACTIONS as _CONFLICT_ACTIONS,
    _is_valid_parallelism as _is_valid_parallelism,
)

from hpc_gui.config.settings_store import (
    SBATCH_FOLLOW_MODES,
    SBATCH_FOLLOW_MODE_NEW_TABS_SPLIT,
    SBATCH_FOLLOW_MODE_NEW_WINDOWS_SPLIT,
    SBATCH_FOLLOW_MODE_NEW_WINDOW_COMBINED,
    SBATCH_FOLLOW_MODE_NONE,
    SBATCH_FOLLOW_MODE_OUTPUTS_TAB,
    clear_file_association,
    get_cli_default_profile,
    get_cli_external_access_enabled,
    get_file_association,
    get_file_associations,
    get_follow_window_open_minimized_enabled,
    get_ftp_state,
    get_ftp_transfer_type,
    get_hide_finished_jobs_enabled,
    get_jobs_outputs_refresh_interval_seconds,
    get_last_seen_changelog_version,
    get_live_tracking_warning_interval_seconds,
    get_lssrv_auto_refresh_enabled,
    get_pause_live_follow_when_minimized_enabled,
    get_remote_directory_cache_enabled,
    get_sacct_auto_refresh_enabled,
    get_sbatch_follow_mode,
    get_squeue_auto_refresh_enabled,
    get_ssh_connection_attempts,
    get_transfer_checksum_verification_enabled,
    get_transfer_completion_action,
    get_transfer_parallelism,
    get_upload_preflight_confirmation_enabled,
    set_cli_default_profile,
    set_cli_external_access_enabled,
    set_file_association,
    set_ftp_transfer_type,
    set_hide_finished_jobs_enabled,
    set_jobs_outputs_refresh_interval_seconds,
    set_last_seen_changelog_version,
    set_live_tracking_warning_interval_seconds,
    set_lssrv_auto_refresh_enabled,
    set_remote_directory_cache_enabled,
    set_sbatch_follow_mode,
    set_ssh_connection_attempts,
    set_transfer_checksum_verification_enabled,
    set_transfer_completion_action,
    set_transfer_parallelism,
    set_upload_preflight_confirmation_enabled,
    update_ftp_state,
    _TRANSFER_COMPLETION_ACTIONS as _TRANSFER_COMPLETION_ACTIONS,
    _coerce_int_in_range as _coerce_int_in_range,
    _coerce_positive_int as _coerce_positive_int,
    _normalize_file_extension as _normalize_file_extension,
)

from hpc_gui.config.window_state import (
    MAIN_WINDOW_STATE_KEY,
    clear_main_window_state,
    get_main_window_state,
    get_ui_pref_bool,
    save_main_window_state,
    set_ui_pref_bool,
)


_config_dir = _ORIGINAL_CONFIG_DIR
_config_path = _ORIGINAL_CONFIG_PATH


def _compat_config_path() -> Path:
    """Resolve either legacy facade patches or storage-IO patches."""
    facade_provider = globals()["_config_path"]
    if facade_provider is not _ORIGINAL_CONFIG_PATH:
        return Path(facade_provider())
    io_provider = _storage_io._config_path
    if io_provider is not _ORIGINAL_CONFIG_PATH:
        return Path(io_provider())
    facade_dir = globals()["_config_dir"]
    if facade_dir is not _ORIGINAL_CONFIG_DIR:
        return Path(facade_dir()) / "config.json"
    io_dir = _storage_io._config_dir
    if io_dir is not _ORIGINAL_CONFIG_DIR:
        return Path(io_dir()) / "config.json"
    return _storage_io._default_config_path()


def save_config(cfg: dict[str, Any]) -> None:
    """Persist config while preserving the facade's historical path seam."""
    _storage_io._save_config_payload(cfg, _compat_config_path())


def load_config() -> dict[str, Any]:
    with _storage_io._compat_config_io(_compat_config_path, save_config):
        return _load_config_impl()


def _with_compat_config_io(function: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(function)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        with _storage_io._compat_config_io(
            _compat_config_path, lambda cfg: save_config(cfg)
        ):
            with _settings_compat.bind_settings_facade(
                lambda: load_settings(), lambda patch: update_settings(patch)
            ):
                return function(*args, **kwargs)

    return wrapped


_COMPATIBLE_MODULES = {
    "hpc_gui.config.profiles_store",
    "hpc_gui.config.settings_store",
    "hpc_gui.config.storage_io",
    "hpc_gui.config.window_state",
}
for _name, _value in tuple(globals().items()):
    if (
        not _name.startswith("_")
        and _name != "save_config"
        and callable(_value)
        and getattr(_value, "__module__", "") in _COMPATIBLE_MODULES
    ):
        globals()[_name] = _with_compat_config_io(_value)

__all__ = [
    "MAIN_WINDOW_STATE_KEY",
    "SBATCH_FOLLOW_MODES",
    "SBATCH_FOLLOW_MODE_NEW_TABS_SPLIT",
    "SBATCH_FOLLOW_MODE_NEW_WINDOWS_SPLIT",
    "SBATCH_FOLLOW_MODE_NEW_WINDOW_COMBINED",
    "SBATCH_FOLLOW_MODE_NONE",
    "SBATCH_FOLLOW_MODE_OUTPUTS_TAB",
    "clear_file_association",
    "clear_main_window_state",
    "clear_profile_conflict_action",
    "coerce_profile_ssh_timeout",
    "coerce_profile_transfer_parallelism",
    "delete_profile",
    "get_cli_default_profile",
    "get_cli_external_access_enabled",
    "get_file_association",
    "get_file_associations",
    "get_follow_window_open_minimized_enabled",
    "get_ftp_state",
    "get_ftp_transfer_type",
    "get_hide_finished_jobs_enabled",
    "get_jobs_outputs_refresh_interval_seconds",
    "get_last_profile_name",
    "get_last_seen_changelog_version",
    "get_live_tracking_warning_interval_seconds",
    "get_lssrv_auto_refresh_enabled",
    "get_main_window_state",
    "get_pause_live_follow_when_minimized_enabled",
    "get_profile_conflict_action",
    "get_profile_id",
    "get_remote_directory_cache_enabled",
    "get_sacct_auto_refresh_enabled",
    "get_sbatch_follow_mode",
    "get_squeue_auto_refresh_enabled",
    "get_ssh_connection_attempts",
    "get_transfer_checksum_verification_enabled",
    "get_transfer_completion_action",
    "get_transfer_parallelism",
    "get_ui_pref_bool",
    "get_upload_preflight_confirmation_enabled",
    "load_config",
    "load_profiles",
    "load_settings",
    "merge_profile_patch",
    "migrate_legacy_transfer_parallelism",
    "resolve_provider_overrides",
    "save_config",
    "save_main_window_state",
    "set_cli_default_profile",
    "set_cli_external_access_enabled",
    "set_file_association",
    "set_ftp_transfer_type",
    "set_hide_finished_jobs_enabled",
    "set_jobs_outputs_refresh_interval_seconds",
    "set_last_seen_changelog_version",
    "set_live_tracking_warning_interval_seconds",
    "set_lssrv_auto_refresh_enabled",
    "set_profile_conflict_action",
    "set_remote_directory_cache_enabled",
    "set_sbatch_follow_mode",
    "set_ssh_connection_attempts",
    "set_transfer_checksum_verification_enabled",
    "set_transfer_completion_action",
    "set_transfer_parallelism",
    "set_ui_pref_bool",
    "set_upload_preflight_confirmation_enabled",
    "update_ftp_state",
    "update_settings",
    "upsert_profile",
]

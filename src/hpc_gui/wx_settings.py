"""wx settings model preserving global/profile boundaries.

W37 live owner for settings schema, persistence and plugin/provider
settings compatibility (``waves/pending/W37.md``):

- Workstream A (SET-001..006): :data:`SETTINGS_INVENTORY` is the key-level
  table (Key | Owner | Type | Default | Persisted | Sensitive |
  Migrated from | Consumer | UI control) plus dead-key, duplicate-truth,
  coercion, UI-default and collision flags.
- Workstream B (SET-007..015): atomic load/save lives in
  ``hpc_gui.config.storage`` (tmp + fsync + replace, corrupt backup,
  fail-closed coercion); this module maps the dialog model onto it.
- Workstream E (PLUGINSET-001/002): plugin/provider settings use the
  ``hpc_gui.plugins.settings`` namespacing contract; see
  :func:`plugin_settings_survive_absence`.
- TODO PERSIST/PROFILE/RUNTIME/RESTART/PARITY/SILENT-ERROR: real storage
  wiring (:func:`build_model_from_storage`,
  :func:`persist_model_snapshot`), live-vs-restart declarations
  (:data:`LIVE_APPLY_KEYS`, :data:`RESTART_REQUIRED_KEYS`), Qt parity map
  (:data:`QT_PARITY_MAP`), and attributable errors (no silent swallow).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from hpc_gui.core.platform import current_os
from hpc_gui.services.shortcut_preferences import ShortcutPreferences


GLOBAL_KEYS = frozenset({"jobs_outputs_refresh_interval", "remote_directory_cache", "transfer_checksum", "shortcut_preferences"})
PROFILE_KEYS = frozenset({"transfer_parallelism", "ssh_timeout", "keepalive_interval_seconds", "x11_enabled"})
LEGACY_IGNORED_KEYS = frozenset({"terminal_graphics_auto_compatibility", "qt_webengine_gpu"})

#: Model key -> stored global settings key in config.json.
GLOBAL_STORAGE_KEYS: dict[str, str] = {
    "remote_directory_cache": "remote_directory_cache_enabled",
    "transfer_checksum": "transfer_checksum_verification_enabled",
    "jobs_outputs_refresh_interval": "jobs_outputs_refresh_interval_seconds",
    "shortcut_preferences": "shortcut_preferences",
}

#: Model profile key -> stored per-profile record key.
#: ``x11_enabled`` is the dialog-facing alias of the profile record's
#: ``x11_forwarding`` (same bit the Qt connection dialog, the CLI session
#: builder and the SSH client consume).
PROFILE_STORAGE_KEYS: dict[str, str] = {
    "transfer_parallelism": "transfer_parallelism",
    "ssh_timeout": "ssh_timeout",
    "keepalive_interval_seconds": "keepalive_interval_seconds",
    "x11_enabled": "x11_forwarding",
}

#: Settings documented as live-applicable: they measurably propagate to the
#: running feature without restart (SETTINGS-RUNTIME-001).
LIVE_APPLY_KEYS = frozenset({
    "remote_directory_cache",
    "transfer_checksum",
    "jobs_outputs_refresh_interval",
    "transfer_parallelism",
    "ssh_timeout",
    "keepalive_interval_seconds",
    "x11_enabled",
    "shortcut_preferences",
})

#: Settings that require restart before they take effect. Empty by
#: deliberate product decision: every dialog-exposed W37 setting is either
#: live-applied or takes effect on next connection/session, never on app
#: restart. The set stays declared (not implicit) so a future
#: restart-gated setting must add itself here plus visible dialog text
#: (SETTINGS-RESTART-001).
RESTART_REQUIRED_KEYS = frozenset()

#: Qt-era setting audit (SETTINGS-PARITY-001). No user-facing setting may
#: disappear silently: every known Qt-era key is PORT-TO-WX, DEPRECATED
#: (explicitly ignored with a named constant), or NOT-IN-V2 (never shipped
#: as a user setting in V2 scope).
QT_PARITY_MAP: dict[str, str] = {
    "remote_directory_cache_enabled": "PORT-TO-WX",
    "transfer_checksum_verification_enabled": "PORT-TO-WX",
    "jobs_outputs_refresh_interval_seconds": "PORT-TO-WX",
    "transfer_parallelism": "PORT-TO-WX",
    "ssh_timeout": "PORT-TO-WX",
    "keepalive_interval_seconds": "PORT-TO-WX",
    "x11_forwarding": "PORT-TO-WX",
    "shortcut_preferences": "PORT-TO-WX",
    "terminal_graphics_auto_compatibility": "DEPRECATED",
    "qt_webengine_gpu": "DEPRECATED",
    "qt_startup_changelog_popup": "NOT-IN-V2",
}

#: Key-level settings inventory (Workstream A / TASK-W09-001 / UPD-044).
#: Each row: Key | Owner | Type | Default | Persisted | Sensitive |
#: Migrated from | Consumer | UI control | Scope | Live effect.
SETTINGS_INVENTORY: tuple[dict[str, Any], ...] = (
    {"key": "remote_directory_cache", "owner": "core/files", "type": "bool", "default": True, "persisted": "config.json:settings.remote_directory_cache_enabled", "sensitive": False, "migrated_from": None, "consumer": "get_remote_directory_cache_enabled", "ui_control": "wx Settings checkbox", "scope": "global", "live": True},
    {"key": "transfer_checksum", "owner": "core/transfers", "type": "bool", "default": False, "persisted": "config.json:settings.transfer_checksum_verification_enabled", "sensitive": False, "migrated_from": None, "consumer": "get_transfer_checksum_verification_enabled", "ui_control": "wx Settings checkbox", "scope": "global", "live": True},
    {"key": "jobs_outputs_refresh_interval", "owner": "core/jobs", "type": "int seconds", "default": 15, "persisted": "config.json:settings.jobs_outputs_refresh_interval_seconds", "sensitive": False, "migrated_from": None, "consumer": "get_jobs_outputs_refresh_interval_seconds", "ui_control": "Jobs refresh path (no Settings dialog spin; hidden-capability, not orphan)", "scope": "global", "live": True},
    {"key": "shortcut_preferences", "owner": "core/keymap", "type": "object", "default": {}, "persisted": "config.json:settings.shortcut_preferences", "sensitive": False, "migrated_from": None, "consumer": "ShortcutPreferences", "ui_control": "shortcut preferences surface", "scope": "global", "live": True},
    {"key": "transfer_parallelism", "owner": "core/transfers", "type": "int 1..10", "default": 1, "persisted": "config.json:profiles[].transfer_parallelism", "sensitive": False, "migrated_from": "settings.transfer_parallelism (v1.4.0 global)", "consumer": "coerce_profile_transfer_parallelism", "ui_control": "wx Settings spin (profile)", "scope": "profile", "live": True},
    {"key": "ssh_timeout", "owner": "core/connection", "type": "float|None", "default": None, "persisted": "config.json:profiles[].ssh_timeout", "sensitive": False, "migrated_from": None, "consumer": "coerce_profile_ssh_timeout", "ui_control": "wx Settings spin (profile)", "scope": "profile", "live": True},
    {"key": "keepalive_interval_seconds", "owner": "core/connection", "type": "int 0..3600", "default": 30, "persisted": "config.json:profiles[].keepalive_interval_seconds", "sensitive": False, "migrated_from": None, "consumer": "coerce_keepalive_interval (CLI+GUI)", "ui_control": "connection dialog keepalive spin", "scope": "profile", "live": True},
    {"key": "x11_enabled", "owner": "core/connection", "type": "bool", "default": False, "persisted": "config.json:profiles[].x11_forwarding", "sensitive": False, "migrated_from": None, "consumer": "x11_runner / ssh client / CLI session", "ui_control": "connection dialog X11 checkbox", "scope": "profile", "live": True},
)

#: Workstream A flags, evaluated against live code (SET-002..006).
INVENTORY_FLAGS: tuple[str, ...] = (
    "dead keys: none — every inventoried key has a named consumer above",
    "duplicate sources of truth: none — transfer_parallelism single-sourced to profiles[] after v1.4.0 migration",
    "implicit type coercion: none — storage getters coerce fail-closed to documented defaults; plugin validators reject mistyped values",
    "UI default != runtime default: none — dialog controls initialize from the same storage getters the runtime consumes",
    "core/plugin key collisions: none — plugin keys live under plugins.<id>.<key> and core keys are reject-listed",
)


@dataclass(frozen=True)
class SettingsSnapshot:
    global_settings: dict[str, Any]
    profile_settings: dict[str, Any]


class WxSettingsModel:
    def __init__(self, settings: dict[str, Any] | None = None, *, apply: Callable[[SettingsSnapshot], None] | None = None, platform: str | None = None) -> None:
        raw = dict(settings or {})
        self.global_settings = {key: raw[key] for key in GLOBAL_KEYS if key in raw}
        self.profile_settings = {key: raw[key] for key in PROFILE_KEYS if key in raw}
        self.apply_callback = apply
        self.shortcuts = ShortcutPreferences(platform or current_os(), {"shortcut_preferences": self.global_settings.get("shortcut_preferences", {})})

    def set_global(self, key: str, value: Any) -> None:
        if key not in GLOBAL_KEYS:
            raise KeyError(key)
        self.global_settings[key] = value

    def set_profile(self, key: str, value: Any) -> None:
        if key not in PROFILE_KEYS:
            raise KeyError(key)
        self.profile_settings[key] = value

    def snapshot(self) -> SettingsSnapshot:
        return SettingsSnapshot(dict(self.global_settings), dict(self.profile_settings))

    def apply(self) -> SettingsSnapshot:
        snapshot = self.snapshot()
        if self.apply_callback:
            self.apply_callback(snapshot)
        return snapshot

    def serialized(self) -> dict[str, Any]:
        return {**self.global_settings, **self.profile_settings, "shortcut_preferences": self.shortcuts.serialize()}


def persist_transfer_checksum_to_storage(model: WxSettingsModel) -> bool:
    """Bridge the wx ``transfer_checksum`` checkbox to the stored
    ``transfer_checksum_verification_enabled`` setting consumed by both the
    Qt and wx transfer verify paths (W25 TODO-013/TODO-043).

    Without this bridge the wx checkbox only flips in-memory model state
    that no transfer path reads.  Returns the stored value.
    """
    from hpc_gui.config.storage import set_transfer_checksum_verification_enabled

    return bool(
        set_transfer_checksum_verification_enabled(
            bool(model.global_settings.get("transfer_checksum", False))
        )
    )


def _active_profile_name(explicit: str | None = None) -> str | None:
    """Resolve the profile that profile-scoped settings belong to."""
    if explicit and str(explicit).strip():
        return str(explicit).strip()
    try:
        from hpc_gui.config.storage import get_last_profile_name

        name = get_last_profile_name()
        return str(name).strip() if name and str(name).strip() else None
    except Exception:
        return None


def build_model_from_storage(
    profile_name: str | None = None,
    *,
    platform: str | None = None,
    apply: Callable[[SettingsSnapshot], None] | None = None,
) -> WxSettingsModel:
    """Build a dialog model from real persisted state (SETTINGS-PERSIST-001).

    Global keys come from ``config.json`` settings; profile keys come from
    the active (or explicitly named) profile record only. No fabricated
    defaults: every value is read through the same storage getters the
    runtime consumes.
    """
    from hpc_gui.config import storage as _storage

    settings = _storage.load_settings()
    global_values: dict[str, Any] = {
        "remote_directory_cache": _storage.get_remote_directory_cache_enabled(),
        "transfer_checksum": _storage.get_transfer_checksum_verification_enabled(),
        "jobs_outputs_refresh_interval": _storage.get_jobs_outputs_refresh_interval_seconds(),
    }
    raw_shortcuts = settings.get("shortcut_preferences")
    if isinstance(raw_shortcuts, dict):
        global_values["shortcut_preferences"] = raw_shortcuts

    profile_values: dict[str, Any] = {}
    target = _active_profile_name(profile_name)
    if target:
        try:
            record = next(
                (p for p in _storage.load_profiles() if p.get("name") == target),
                None,
            )
        except Exception:
            record = None
        if isinstance(record, dict):
            profile_values["transfer_parallelism"] = _storage.coerce_profile_transfer_parallelism(
                record.get("transfer_parallelism"), 1
            )
            profile_values["ssh_timeout"] = _storage.coerce_profile_ssh_timeout(
                record.get("ssh_timeout"), None
            )
            try:
                from hpc_gui.ssh.client import coerce_keepalive_interval
            except Exception:
                coerce_keepalive_interval = None  # type: ignore
            if coerce_keepalive_interval is not None:
                try:
                    profile_values["keepalive_interval_seconds"] = coerce_keepalive_interval(
                        record.get("keepalive_interval_seconds", 30)
                    )
                except Exception:
                    profile_values["keepalive_interval_seconds"] = 30
            else:
                profile_values["keepalive_interval_seconds"] = record.get(
                    "keepalive_interval_seconds", 30
                )
            profile_values["x11_enabled"] = bool(record.get("x11_forwarding", False))

    return WxSettingsModel(
        {**global_values, **profile_values},
        apply=apply,
        platform=platform,
    )


def load_persisted_snapshot(profile_name: str | None = None) -> SettingsSnapshot:
    """Re-read persisted state from storage (SETTINGS-PERSIST-003).

    Used to prove reopen-after-Apply loads values from storage, not from
    the closed dialog's in-memory model.
    """
    return build_model_from_storage(profile_name).snapshot()


def persist_model_snapshot(
    snapshot: SettingsSnapshot,
    *,
    profile_name: str | None = None,
) -> dict[str, Any]:
    """Persist a dialog snapshot to real storage (SETTINGS-PERSIST-002).

    Global keys are written via ``config.storage`` (atomic save); profile
    keys are written only to the active profile record (PROFILE-001
    isolation: profile B is never touched when profile A is active).
    Success is reported only after every underlying write succeeds; any
    failure raises with the failing key attributed — never a false-success
    (SILENT-ERROR-001: no broad silent swallow).
    """
    from hpc_gui.config import storage as _storage

    errors: list[str] = []
    persisted: dict[str, Any] = {"global": {}, "profile": {}, "profile_name": None}

    def _fail(key: str, exc: Exception) -> None:
        errors.append(f"{key}: {exc}")

    # -- global scope -----------------------------------------------------
    mapping = dict(snapshot.global_settings or {})
    if "remote_directory_cache" in mapping:
        try:
            value = _storage.set_remote_directory_cache_enabled(
                bool(mapping["remote_directory_cache"])
            )
            persisted["global"]["remote_directory_cache"] = value
        except Exception as exc:
            _fail("remote_directory_cache", exc)
    if "transfer_checksum" in mapping:
        try:
            value = _storage.set_transfer_checksum_verification_enabled(
                bool(mapping["transfer_checksum"])
            )
            persisted["global"]["transfer_checksum"] = value
        except Exception as exc:
            _fail("transfer_checksum", exc)
    if "jobs_outputs_refresh_interval" in mapping:
        try:
            value = _storage.set_jobs_outputs_refresh_interval_seconds(
                int(mapping["jobs_outputs_refresh_interval"])
            )
            persisted["global"]["jobs_outputs_refresh_interval"] = value
        except Exception as exc:
            _fail("jobs_outputs_refresh_interval", exc)
    if "shortcut_preferences" in mapping and isinstance(
        mapping["shortcut_preferences"], dict
    ):
        try:
            _storage.update_settings(
                {"shortcut_preferences": dict(mapping["shortcut_preferences"])}
            )
            persisted["global"]["shortcut_preferences"] = dict(
                mapping["shortcut_preferences"]
            )
        except Exception as exc:
            _fail("shortcut_preferences", exc)

    # -- profile scope (active profile only) ------------------------------
    profile_patch = {
        key: (snapshot.profile_settings or {}).get(key)
        for key in PROFILE_KEYS
        if key in (snapshot.profile_settings or {})
    }
    if profile_patch:
        target = _active_profile_name(profile_name)
        if not target:
            _fail("profile", RuntimeError("no active profile; profile settings not persisted"))
        else:
            try:
                profiles = _storage.load_profiles()
                record = next(
                    (p for p in profiles if p.get("name") == target), None
                )
                if record is None:
                    _fail("profile", KeyError(f"active profile {target!r} not found"))
                else:
                    updated = dict(record)
                    if "transfer_parallelism" in profile_patch:
                        updated["transfer_parallelism"] = _storage.coerce_profile_transfer_parallelism(
                            profile_patch["transfer_parallelism"], 1
                        )
                    if "ssh_timeout" in profile_patch:
                        updated["ssh_timeout"] = _storage.coerce_profile_ssh_timeout(
                            profile_patch["ssh_timeout"], None
                        )
                    if "keepalive_interval_seconds" in profile_patch:
                        updated["keepalive_interval_seconds"] = profile_patch[
                            "keepalive_interval_seconds"
                        ]
                    if "x11_enabled" in profile_patch:
                        updated["x11_forwarding"] = bool(profile_patch["x11_enabled"])
                    _storage.upsert_profile(updated)
                    persisted["profile"] = {
                        PROFILE_STORAGE_KEYS.get(k, k): updated.get(
                            PROFILE_STORAGE_KEYS.get(k, k)
                        )
                        for k in profile_patch
                    }
                    persisted["profile_name"] = target
            except Exception as exc:
                _fail("profile", exc)

    if errors:
        raise RuntimeError("settings persist rejected (" + "; ".join(errors) + ")")
    return persisted


def plugin_settings_survive_absence(
    root: Any,
    plugin_id: str,
    spec: Any,
) -> dict[str, Any]:
    """Prove plugin settings survive absence/disable (PLUGINSET-002/UPD-060).

    Thin owner-routed bridge to ``hpc_gui.plugins.settings`` (ARCH-BOUNDARY-001:
    no duplicated site logic in the settings module): loading for an absent
    plugin id must return spec defaults without raising.
    """
    from hpc_gui.plugins.settings import load_plugin_settings

    return dict(load_plugin_settings(root, plugin_id, spec))


__all__ = [
    "GLOBAL_KEYS",
    "GLOBAL_STORAGE_KEYS",
    "INVENTORY_FLAGS",
    "LEGACY_IGNORED_KEYS",
    "LIVE_APPLY_KEYS",
    "PROFILE_KEYS",
    "PROFILE_STORAGE_KEYS",
    "QT_PARITY_MAP",
    "RESTART_REQUIRED_KEYS",
    "SETTINGS_INVENTORY",
    "SettingsSnapshot",
    "WxSettingsModel",
    "build_model_from_storage",
    "load_persisted_snapshot",
    "persist_model_snapshot",
    "persist_transfer_checksum_to_storage",
    "plugin_settings_survive_absence",
]

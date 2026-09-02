"""wx settings model preserving global/profile boundaries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from hpc_gui.services.shortcut_preferences import ShortcutPreferences


GLOBAL_KEYS = frozenset({"jobs_outputs_refresh_interval", "remote_directory_cache", "transfer_checksum", "shortcut_preferences"})
PROFILE_KEYS = frozenset({"transfer_parallelism", "ssh_timeout", "keepalive_interval_seconds", "x11_enabled"})
LEGACY_IGNORED_KEYS = frozenset({"terminal_graphics_auto_compatibility", "qt_webengine_gpu"})


@dataclass(frozen=True)
class SettingsSnapshot:
    global_settings: dict[str, Any]
    profile_settings: dict[str, Any]


class WxSettingsModel:
    def __init__(self, settings: dict[str, Any] | None = None, *, apply: Callable[[SettingsSnapshot], None] | None = None) -> None:
        raw = dict(settings or {})
        self.global_settings = {key: raw[key] for key in GLOBAL_KEYS if key in raw}
        self.profile_settings = {key: raw[key] for key in PROFILE_KEYS if key in raw}
        self.apply_callback = apply
        self.shortcuts = ShortcutPreferences("windows", {"shortcut_preferences": self.global_settings.get("shortcut_preferences", {})})

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


__all__ = ["LEGACY_IGNORED_KEYS", "SettingsSnapshot", "WxSettingsModel"]

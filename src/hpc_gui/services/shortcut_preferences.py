"""Versioned, framework-neutral shortcut preference storage."""

from __future__ import annotations

from typing import Any

from hpc_gui.config.storage import load_settings, update_settings
from hpc_gui.services.platform_keymap import KeyBinding, bindings_for, display_binding


SCHEMA_VERSION = 1
SETTINGS_KEY = "shortcut_preferences"
KEYMAP_MODES = {"standard", "legacy"}


def migrate_keymap_settings(settings: dict[str, Any] | None, mode: str | None = None) -> dict[str, Any]:
    """Add the one-time keymap choice without changing existing bindings."""
    result = dict(settings or {})
    stored = result.get(SETTINGS_KEY)
    stored = stored if isinstance(stored, dict) else {}
    if "keymap_mode" not in stored:
        chosen = mode or "standard"
        if chosen not in KEYMAP_MODES:
            raise ValueError(f"unsupported keymap mode: {chosen}")
        result[SETTINGS_KEY] = {**stored, "keymap_mode": chosen}
    return result


def active_binding(command_id: str, platform: str, settings: dict[str, Any] | None = None) -> str | None:
    """Return the first active display binding for a command."""
    return next(
        (display_binding(item.binding, platform) for item in ShortcutPreferences(platform, settings).bindings() if item.command_id == command_id),
        None,
    )


class ShortcutPreferences:
    def __init__(self, platform: str, settings: dict[str, Any] | None = None) -> None:
        self.platform = platform
        stored = (settings if settings is not None else load_settings()).get(SETTINGS_KEY, {})
        stored = stored if isinstance(stored, dict) else {}
        mode = stored.get("keymap_mode", "standard")
        self._keymap_mode = mode if mode in KEYMAP_MODES else "standard"
        defaults = bindings_for("windows" if self._keymap_mode == "legacy" else platform)
        self._defaults = tuple(defaults)
        self._bindings = list(defaults)
        custom = stored.get("bindings", stored if "version" not in stored else {})
        if isinstance(custom, dict):
            self._bindings = [item for item in defaults if item.command_id not in custom]
            for command_id, value in custom.items():
                if isinstance(value, list):
                    template = next((item for item in defaults if item.command_id == command_id), None)
                    if template is not None:
                        self._bindings.extend(KeyBinding(command_id, str(binding), template.context) for binding in value if str(binding).strip())

    def bindings(self) -> tuple[KeyBinding, ...]:
        return tuple(self._bindings)

    def set_binding(self, command_id: str, binding: str) -> None:
        binding = binding.strip()
        template = next((item for item in self._defaults if item.command_id == command_id), None)
        if template is None:
            raise KeyError(f"unknown shortcut command: {command_id}")
        if not binding:
            raise ValueError("binding cannot be empty")
        if any(item.command_id != command_id and item.binding == binding and item.context == template.context for item in self._bindings):
            raise ValueError(f"shortcut conflict: {binding} in {template.context}")
        self.remove(command_id)
        self._bindings.append(KeyBinding(command_id, binding, template.context))

    def remove(self, command_id: str) -> None:
        if not any(item.command_id == command_id for item in self._bindings):
            raise KeyError(f"unknown shortcut command: {command_id}")
        self._bindings = [item for item in self._bindings if item.command_id != command_id]

    def reset_command(self, command_id: str) -> None:
        self.remove(command_id)
        self._bindings.extend(item for item in self._defaults if item.command_id == command_id)

    def reset_category(self, category: str) -> None:
        command_ids = {item.command_id for item in self._defaults if item.context == category}
        self._bindings = [item for item in self._bindings if item.command_id not in command_ids]
        self._bindings.extend(item for item in self._defaults if item.command_id in command_ids)

    def reset_all(self) -> None:
        self._bindings = list(self._defaults)

    def conflicts(self) -> tuple[tuple[KeyBinding, KeyBinding], ...]:
        result = []
        for index, left in enumerate(self._bindings):
            for right in self._bindings[index + 1 :]:
                if left.binding == right.binding and left.context == right.context and left.command_id != right.command_id:
                    result.append((left, right))
        return tuple(result)

    def serialize(self) -> dict[str, Any]:
        grouped: dict[str, list[str]] = {}
        for item in self._bindings:
            grouped.setdefault(item.command_id, []).append(item.binding)
        return {"version": SCHEMA_VERSION, "platform": self.platform, "keymap_mode": self._keymap_mode, "bindings": grouped}

    def persist(self) -> dict[str, Any]:
        value = self.serialize()
        update_settings({SETTINGS_KEY: value})
        return value

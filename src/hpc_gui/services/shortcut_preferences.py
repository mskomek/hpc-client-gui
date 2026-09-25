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
    #: Top-level keys owned by this module. Anything else is a future/
    #: unknown key that migration must preserve byte-for-byte
    #: (HPC-W09-MIG-003 / HPC-W09-TODO-MIGRATION-UNKNOWN-001).
    _KNOWN_TOP_LEVEL_KEYS = frozenset({"version", "platform", "keymap_mode", "bindings"})

    def __init__(self, platform: str, settings: dict[str, Any] | None = None) -> None:
        self.platform = platform
        stored = (settings if settings is not None else load_settings()).get(SETTINGS_KEY, {})
        stored = stored if isinstance(stored, dict) else {}
        mode = stored.get("keymap_mode", "standard")
        self._keymap_mode = mode if mode in KEYMAP_MODES else "standard"
        # Preserve unknown/future top-level keys (newer-version safety):
        # they survive round-trips even though this version does not interpret
        # them. Idempotent: re-loading an already-migrated value is a no-op.
        self._unknown_top_level: dict[str, Any] = {
            key: value
            for key, value in stored.items()
            if key not in self._KNOWN_TOP_LEVEL_KEYS
        }
        defaults = bindings_for("windows" if self._keymap_mode == "legacy" else platform)
        self._defaults = tuple(defaults)
        self._bindings = list(defaults)
        custom = stored.get("bindings", stored if "version" not in stored else {})
        # Unknown/future command ids (bindings for commands this version does
        # not know) must survive migration instead of being dropped.
        self._unknown_commands: dict[str, Any] = {}
        if isinstance(custom, dict):
            self._bindings = [item for item in defaults if item.command_id not in custom]
            for command_id, value in custom.items():
                if isinstance(value, list):
                    template = next((item for item in defaults if item.command_id == command_id), None)
                    if template is not None:
                        self._bindings.extend(KeyBinding(command_id, str(binding), template.context) for binding in value if str(binding).strip())
                    else:
                        # Future command: keep the raw binding list verbatim.
                        kept = [str(binding) for binding in value if str(binding).strip()]
                        if kept:
                            self._unknown_commands[str(command_id)] = kept
                elif command_id not in {item.command_id for item in defaults}:
                    # Non-list future payload: preserve verbatim.
                    self._unknown_commands[str(command_id)] = value

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
        # Re-attach preserved future/unknown command bindings verbatim so a
        # newer-version keymap round-trips without data loss.
        for command_id, value in self._unknown_commands.items():
            if command_id not in grouped:
                grouped[command_id] = value if isinstance(value, list) else value
        payload: dict[str, Any] = {"version": SCHEMA_VERSION, "platform": self.platform, "keymap_mode": self._keymap_mode, "bindings": grouped}
        # Re-attach preserved unknown top-level keys last (never overwrite
        # owned keys even if a future version reuses the name differently).
        for key, value in self._unknown_top_level.items():
            payload.setdefault(key, value)
        return payload

    def persist(self) -> dict[str, Any]:
        value = self.serialize()
        update_settings({SETTINGS_KEY: value})
        return value

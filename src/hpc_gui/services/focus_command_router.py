"""Resolve commands by focused context without capturing native text/terminal keys."""

from __future__ import annotations

from hpc_gui.services.command_registry import COMMAND_REGISTRY, CommandDefinition, CommandRegistry


_TERMINAL_CONTROL_KEYS = {"Ctrl+C", "Ctrl+Z"}
_NATIVE_TEXT_KEYS = {"Ctrl+C", "Ctrl+X", "Ctrl+V", "Ctrl+Z", "Ctrl+Y", "Ctrl+A"}


class FocusCommandRouter:
    def __init__(self, registry: CommandRegistry = COMMAND_REGISTRY) -> None:
        self.registry = registry

    def resolve(self, binding: str, context: str, *, text_input: bool = False) -> CommandDefinition | None:
        if context == "terminal" and binding in _TERMINAL_CONTROL_KEYS:
            return None
        if text_input and binding in _NATIVE_TEXT_KEYS:
            return None
        for command in self.registry.all():
            if command.context == context and binding in command.default_bindings:
                return command
        return None

"""Searchable command-palette model backed only by command IDs."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from hpc_gui.services.command_registry import COMMAND_REGISTRY, CommandDefinition, CommandRegistry


@dataclass(frozen=True)
class PaletteItem:
    command: CommandDefinition
    enabled: bool


class CommandPalette:
    def __init__(self, registry: CommandRegistry = COMMAND_REGISTRY) -> None:
        self.registry = registry

    def items(self, context: str | None = None) -> tuple[PaletteItem, ...]:
        return tuple(
            PaletteItem(command, context is None or command.context in {context, "shell"})
            for command in self.registry.all()
        )

    def search(self, query: str = "", context: str | None = None) -> tuple[PaletteItem, ...]:
        needle = query.strip().casefold()
        candidates = self.items(context)
        if not needle:
            return candidates

        def score(item: PaletteItem) -> tuple[int, str]:
            command = item.command
            fields = (command.label().casefold(), command.category.casefold(), command.help_key.casefold(), command.id.casefold())
            rank = 0 if fields[0] == needle else 1 if fields[0].startswith(needle) else 2 if any(needle in field for field in fields) else 99
            return rank, command.id

        return tuple(sorted((item for item in candidates if score(item)[0] < 99), key=score))

    def execute(self, command_id: str, context: str, handlers: dict[str, Callable[[], object]]) -> object:
        item = next((item for item in self.items(context) if item.command.id == command_id), None)
        if item is None or not item.enabled:
            raise PermissionError(f"command unavailable in context: {command_id}")
        try:
            handler = handlers[command_id]
        except KeyError as exc:
            raise KeyError(f"no handler for command: {command_id}") from exc
        return handler()

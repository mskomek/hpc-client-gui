"""Framework-neutral command metadata for menus, help and shortcut clients."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable

from hpc_gui.core.i18n import t


@dataclass(frozen=True)
class CommandDefinition:
    id: str
    label_key: str
    category: str
    context: str
    help_key: str
    default_bindings: tuple[str, ...] = ()

    def label(self) -> str:
        return t(self.label_key)

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["default_bindings"] = list(self.default_bindings)
        return value


_COMMANDS = (
    CommandDefinition("APP-CONNECT", "login.connect", "application", "profile", "login.connect"),
    CommandDefinition("APP-DISCONNECT", "login.disconnect", "application", "session", "login.disconnect"),
    CommandDefinition("APP-SETTINGS", "settings.action", "application", "shell", "settings.dialog_title"),
    CommandDefinition("APP-HELP", "help.open_help", "application", "shell", "help.open_help", ("F1",)),
    CommandDefinition("NAV-JOBS", "tabs.jobs_outputs", "navigation", "shell", "tabs.jobs_outputs"),
    CommandDefinition("NAV-DIRECTORIES", "tabs.directories", "navigation", "shell", "tabs.directories"),
    CommandDefinition("NAV-FILES", "tabs.ftp", "navigation", "shell", "tabs.ftp"),
    CommandDefinition("NAV-EDITOR", "tabs.editor", "navigation", "shell", "tabs.editor"),
    CommandDefinition("FILE-REFRESH", "dirs.refresh", "files", "directory", "dirs.refresh", ("F5",)),
    CommandDefinition("FILE-OPEN", "editor.open", "files", "directory", "editor.open"),
    CommandDefinition("FILE-UPLOAD", "ftp.upload", "files", "directory", "ftp.upload"),
    CommandDefinition("FILE-DOWNLOAD", "ftp.download", "files", "directory", "ftp.download"),
    CommandDefinition("EDIT-SAVE", "editor.save", "editor", "editor", "editor.save", ("Ctrl+S",)),
    CommandDefinition("EDIT-SUBMIT", "editor.submit", "editor", "editor", "editor.submit", ("Ctrl+Shift+S",)),
    CommandDefinition("EDIT-LINT", "editor.lint", "editor", "editor", "editor.lint"),
    CommandDefinition("TERM-FOCUS", "tabs.login", "terminal", "terminal", "tabs.login"),
    CommandDefinition("JOB-REFRESH", "jobs.refresh", "jobs", "jobs", "jobs.refresh"),
    CommandDefinition("JOB-CANCEL", "jobs.cancel", "jobs", "jobs", "jobs.cancel"),
    CommandDefinition("PLUGIN-MANAGER", "files.plugins", "plugins", "shell", "files.plugins"),
    CommandDefinition("DIAGNOSTICS-EXPORT", "dirs.export_diagnostics", "diagnostics", "logs", "dirs.export_diagnostics"),
)


class CommandRegistry:
    def __init__(self, commands: Iterable[CommandDefinition] = _COMMANDS) -> None:
        definitions = tuple(commands)
        self._commands = {command.id: command for command in definitions}
        if len(self._commands) != len(definitions):
            raise ValueError("duplicate command id")

    def get(self, command_id: str) -> CommandDefinition:
        try:
            return self._commands[command_id]
        except KeyError as exc:
            raise KeyError(f"unknown command: {command_id}") from exc

    def all(self) -> tuple[CommandDefinition, ...]:
        return tuple(self._commands.values())

    def by_category(self, category: str) -> tuple[CommandDefinition, ...]:
        return tuple(command for command in self.all() if command.category == category)

    def by_context(self, context: str) -> tuple[CommandDefinition, ...]:
        return tuple(command for command in self.all() if command.context == context)

    def serialize(self) -> list[dict[str, Any]]:
        return [command.as_dict() for command in self.all()]


COMMAND_REGISTRY = CommandRegistry()

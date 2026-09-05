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
    CommandDefinition("APP-COMMAND-PALETTE", "common.command_palette", "application", "shell", "common.command_palette", ("Ctrl+Shift+P",)),
    CommandDefinition("NAV-JOBS", "tabs.jobs_outputs", "navigation", "shell", "tabs.jobs_outputs"),
    CommandDefinition("NAV-DIRECTORIES", "tabs.directories", "navigation", "shell", "tabs.directories"),
    CommandDefinition("NAV-FILES", "tabs.ftp", "navigation", "shell", "tabs.ftp"),
    CommandDefinition("NAV-EDITOR", "tabs.editor", "navigation", "shell", "tabs.editor"),
    CommandDefinition("NAV-TERMINAL", "help.section_terminal", "navigation", "shell", "help.section_terminal"),
    CommandDefinition("NAV-LOGS", "tabs.logs", "navigation", "shell", "tabs.logs"),
    CommandDefinition("FILE-REFRESH", "dirs.refresh", "files", "directory", "dirs.refresh", ("F5",)),
    CommandDefinition("FILE-LOCAL-COPY", "dirs.copy", "files", "local_files", "dirs.copy", ("Ctrl+C",)),
    CommandDefinition("FILE-LOCAL-CUT", "dirs.move", "files", "local_files", "dirs.move", ("Ctrl+X",)),
    CommandDefinition("FILE-LOCAL-PASTE", "dirs.paste", "files", "local_files", "dirs.paste", ("Ctrl+V",)),
    CommandDefinition("FILE-REMOTE-COPY", "dirs.copy", "files", "remote_files", "dirs.copy", ("Ctrl+C",)),
    CommandDefinition("FILE-REMOTE-CUT", "dirs.move", "files", "remote_files", "dirs.move", ("Ctrl+X",)),
    CommandDefinition("FILE-REMOTE-PASTE", "dirs.paste", "files", "remote_files", "dirs.paste", ("Ctrl+V",)),
    CommandDefinition("FILE-REMOTE-UNDO", "dirs.undo", "files", "remote_files", "dirs.undo", ("Ctrl+Z",)),
    CommandDefinition("FILE-OPEN", "editor.open", "files", "directory", "editor.open"),
    CommandDefinition("FILE-UPLOAD", "ftp.upload_selected", "files", "directory", "ftp.upload_selected"),
    CommandDefinition("FILE-DOWNLOAD", "ftp.download_selected", "files", "directory", "ftp.download_selected"),
    CommandDefinition("FILE-NEW-FOLDER", "dirs.new_folder", "files", "directory", "dirs.new_folder"),
    CommandDefinition("JOB-TEST-CLUSTER", "common.test_cluster", "diagnostics", "shell", "common.test_cluster"),
    CommandDefinition("EDITOR-NEW-SLURM", "common.new_slurm_script", "editor", "editor", "common.new_slurm_script"),
    CommandDefinition("EDIT-SAVE", "editor.save", "editor", "editor", "editor.save", ("Ctrl+S",)),
    CommandDefinition("EDIT-SUBMIT", "editor.submit", "editor", "editor", "editor.submit", ("Ctrl+Shift+S",)),
    CommandDefinition("EDIT-LINT", "editor.lint", "editor", "editor", "editor.lint"),
    CommandDefinition("EDIT-EXECUTE", "editor.save_submit", "editor", "editor", "editor.save_submit"),
    CommandDefinition("TERM-FOCUS", "tabs.login", "terminal", "terminal", "tabs.login"),
    CommandDefinition("JOB-REFRESH", "jobs.refresh", "jobs", "jobs", "jobs.refresh"),
    CommandDefinition("JOB-CANCEL", "jobs.cancel", "jobs", "jobs", "jobs.cancel"),
    CommandDefinition("PLUGIN-MANAGER", "files.plugins", "plugins", "shell", "files.plugins"),
    CommandDefinition("PLUGIN-ANSYS-LINTER", "files.ansys_lint", "plugins", "editor", "files.ansys_lint"),
    CommandDefinition("DIAGNOSTICS-EXPORT", "logs.export_diagnostics", "diagnostics", "logs", "logs.export_diagnostics"),
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

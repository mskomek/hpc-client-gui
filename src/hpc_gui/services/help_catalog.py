"""Framework-neutral runtime help metadata layered over static Markdown docs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable
from urllib.parse import urlparse

from hpc_gui.core.i18n import current_language, t
from hpc_gui.services.platform_keymap import KeyBinding, bindings_for, display_binding


@dataclass(frozen=True)
class HelpTopic:
    id: str
    title_key: str
    section: str
    keywords: tuple[str, ...] = ()
    command_ids: tuple[str, ...] = ()
    static_library: str | None = None

    def title(self) -> str:
        return t(self.title_key)


@dataclass(frozen=True)
class ShortcutHelpRow:
    command_id: str
    label: str
    binding: str
    context: str


@dataclass(frozen=True)
class HelpNavigationItem:
    id: str
    title_key: str | None = None
    static_library: str | None = None

    def title(self) -> str:
        return t(self.title_key) if self.title_key else self.id


_TOPICS = (
    HelpTopic("help.getting-started", "help.section_getting_started", "getting-started", ("welcome", "first run"), static_library="core"),
    HelpTopic("help.connections", "help.section_connections", "connections", ("ssh", "mfa", "profile"), ("APP-CONNECT",), "core"),
    HelpTopic("help.terminal", "help.section_terminal", "terminal", ("shell", "x11"), ("TERM-FOCUS",), "core"),
    HelpTopic("help.files-transfers", "help.section_files_transfers", "files-transfers", ("sftp", "upload", "download"), ("FILE-UPLOAD", "FILE-DOWNLOAD"), "core"),
    HelpTopic("help.jobs", "help.section_jobs", "jobs", ("slurm", "queue", "output"), ("JOB-REFRESH", "JOB-CANCEL"), "generic"),
    HelpTopic("help.editor", "help.section_editor", "editor", ("script", "lint"), ("EDIT-SAVE", "EDIT-SUBMIT"), "core"),
    HelpTopic("help.plugins", "help.section_plugins", "plugins", ("plugin", "template"), ("PLUGIN-MANAGER",), "generic"),
    HelpTopic("help.ansys", "help.section_ansys", "ansys", ("trusted tool", "journal"), ("PLUGIN-ANSYS-LINTER",), "generic"),
    HelpTopic("help.troubleshooting", "help.section_troubleshooting", "troubleshooting", ("diagnostic", "error"), ("DIAGNOSTICS-EXPORT",), "core"),
    HelpTopic("help.keyboard-shortcuts", "help.section_keyboard_shortcuts", "keyboard-shortcuts", ("shortcut", "key"), ("APP-HELP", "APP-COMMAND-PALETTE"), "core"),
    HelpTopic("help.mouse-gestures", "help.section_mouse_gestures", "mouse-gestures", ("click", "drag", "gesture"), (), "core"),
)


class HelpCatalog:
    def __init__(self, topics: tuple[HelpTopic, ...] = _TOPICS) -> None:
        self._topics = {topic.id: topic for topic in topics}
        if len(self._topics) != len(topics):
            raise ValueError("duplicate help topic id")

    def topics(self) -> tuple[HelpTopic, ...]:
        return tuple(self._topics.values())

    def navigation(self) -> tuple[HelpNavigationItem, ...]:
        items = [HelpNavigationItem(topic.id, topic.title_key) for topic in self.topics()]
        items.extend((HelpNavigationItem("help.library.truba", "help.library_truba"), HelpNavigationItem("help.library.generic", "help.library_generic")))
        return tuple(items)

    def get(self, topic_id: str) -> HelpTopic:
        return self._topics[topic_id]

    def search(self, query: str) -> tuple[HelpTopic, ...]:
        needle = query.strip().casefold()
        if not needle:
            return self.topics()
        return tuple(topic for topic in self.topics() if needle in " ".join((topic.title(), topic.section, topic.id, *topic.keywords)).casefold())

    def render(self, topic_id: str, binding_lookup: Callable[[str], str | None]) -> str:
        topic = self.get(topic_id)
        lines = [f"# {topic.title()}", "", f"Section: {topic.section}"]
        if topic.static_library:
            lines.extend(("", f"Static library: {topic.static_library}"))
        if topic.command_ids:
            lines.extend(("", "Commands:"))
            lines.extend(f"- {command_id}: {binding_lookup(command_id) or t('help.unbound_command')}" for command_id in topic.command_ids)
        return "\n".join(lines)

    def render_page(self, topic_id: str, platform: str, binding_lookup: Callable[[str], str | None]) -> str:
        if topic_id == "help.library.truba":
            from hpc_gui.core.resources import read_doc_text
            return read_doc_text(f"HELP_LIBRARY_TRUBA_{current_language()}.md") or t("help.missing_help_text")
        if topic_id == "help.library.generic":
            from hpc_gui.core.resources import read_doc_text
            return read_doc_text(f"HELP_LIBRARY_GENERIC_{current_language()}.md") or t("help.missing_help_text")
        if topic_id == "help.keyboard-shortcuts":
            rows = self.shortcut_reference(platform)
            return "\n".join([f"# {t('help.section_keyboard_shortcuts')}", "", *[f"- {row.label} — {row.binding} ({row.context})" for row in rows]])
        if topic_id == "help.mouse-gestures":
            return "\n".join([f"# {t('help.section_mouse_gestures')}", "", *[f"- {row.gesture}: {row.behavior}" for row in self.gesture_reference()]])
        return self.render(topic_id, binding_lookup)

    def shortcut_reference(self, platform: str, bindings: tuple[KeyBinding, ...] | None = None) -> tuple[ShortcutHelpRow, ...]:
        active = bindings if bindings is not None else bindings_for(platform)
        from hpc_gui.services.command_registry import COMMAND_REGISTRY

        rows = []
        for item in active:
            try:
                label = COMMAND_REGISTRY.get(item.command_id).label()
            except KeyError:
                label = item.command_id
            rows.append(ShortcutHelpRow(item.command_id, label, display_binding(item.binding, platform), item.context))
        return tuple(rows)

    def gesture_reference(self):
        from hpc_gui.services.gesture_help import load_gesture_help

        return load_gesture_help()


def is_allowed_external_url(url: str, domains: set[str]) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "https" and parsed.hostname in domains


HELP_CATALOG = HelpCatalog()

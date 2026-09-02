"""Deterministic local search across static and structured help sources."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from hpc_gui.services.help_catalog import HELP_CATALOG


@dataclass(frozen=True)
class HelpSearchResult:
    kind: str
    id: str
    title: str
    context: str
    body: str


_INTERACTIONS = (
    HelpSearchResult("interaction", "keyboard.ctrl-z.editor", "Ctrl+Z", "editor", "Editor text undo"),
    HelpSearchResult("interaction", "keyboard.ctrl-z.remote", "Ctrl+Z", "remote_files", "Remote last-move undo"),
    HelpSearchResult("interaction", "keyboard.ctrl-z.terminal", "Ctrl+Z", "terminal", "Remote shell suspend control code"),
    HelpSearchResult("interaction", "pointer.middle-click-folder", "Middle click", "files", "Open directory in a new tab"),
    HelpSearchResult("interaction", "editor.execute", "Execute", "editor", "Submit Slurm files or run shell files"),
)


class HelpSearchIndex:
    def __init__(self, catalog=HELP_CATALOG, docs_root: Path | None = None) -> None:
        self.catalog = catalog
        root = docs_root or Path(__file__).parents[3] / "docs"
        self._static = tuple(
            HelpSearchResult("static", path.stem, path.stem, "static", path.read_text(encoding="utf-8"))
            for path in sorted(root.glob("HELP*.md"))
        )

    def _all(self, platform: str) -> tuple[HelpSearchResult, ...]:
        topics = tuple(HelpSearchResult("topic", topic.id, topic.title(), topic.section, " ".join(topic.keywords)) for topic in self.catalog.topics())
        shortcuts = tuple(HelpSearchResult("shortcut", f"shortcut.{row.command_id}.{row.context}", row.label, row.context, row.binding) for row in self.catalog.shortcut_reference(platform))
        gestures = tuple(HelpSearchResult("gesture", row.id, row.gesture, row.surface, row.behavior) for row in self.catalog.gesture_reference())
        return topics + shortcuts + gestures + _INTERACTIONS + self._static

    def search(self, query: str, *, platform: str = "windows", context: str | None = None) -> tuple[HelpSearchResult, ...]:
        needle = query.strip().casefold().replace("+", " ")
        if not needle:
            return ()
        results = []
        for result in self._all(platform):
            if context is not None and result.context not in {context, "shell", "static"}:
                continue
            haystack = " ".join((result.title, result.context, result.id, result.body)).casefold().replace("+", " ")
            if needle not in haystack:
                continue
            title = result.title.casefold()
            score = 0 if title == needle else 1 if title.startswith(needle) else 2
            results.append((score, result.kind, result.id, result))
        return tuple(item[-1] for item in sorted(results))

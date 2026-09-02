"""Default Windows/Linux bindings, separate from toolkit accelerators."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class KeyBinding:
    command_id: str
    binding: str
    context: str


_COMMON = (
    KeyBinding("APP-SETTINGS", "Ctrl+,", "shell"),
    KeyBinding("APP-COMMAND-PALETTE", "Ctrl+Shift+P", "shell"),
    KeyBinding("APP-HELP", "F1", "shell"),
    KeyBinding("FILE-COPY", "Ctrl+C", "files"),
    KeyBinding("FILE-CUT", "Ctrl+X", "files"),
    KeyBinding("FILE-PASTE", "Ctrl+V", "files"),
    KeyBinding("FILE-SELECT-ALL", "Ctrl+A", "files"),
    KeyBinding("FILE-NEW-FOLDER", "Ctrl+Shift+N", "files"),
    KeyBinding("FILE-RENAME", "F2", "files"),
    KeyBinding("FILE-REFRESH", "F5", "files"),
    KeyBinding("FILE-DELETE", "Delete", "files"),
    KeyBinding("FILE-PARENT", "Alt+Up", "files"),
    KeyBinding("FILE-BACK", "Alt+Left", "files"),
    KeyBinding("FILE-FORWARD", "Alt+Right", "files"),
    KeyBinding("FILE-LOCATION", "Alt+D", "files"),
    KeyBinding("FILE-LOCATION", "Ctrl+L", "files"),
    KeyBinding("FILE-NEW-TAB", "Ctrl+T", "files"),
    KeyBinding("FILE-CLOSE-TAB", "Ctrl+W", "files"),
    KeyBinding("FILE-NEXT-TAB", "Ctrl+Tab", "files"),
    KeyBinding("FILE-FIND", "Ctrl+F", "files"),
    KeyBinding("FILE-CHECKSUM", "Ctrl+Alt+C", "files"),
    KeyBinding("FILE-PROPERTIES", "Alt+Enter", "files"),
    KeyBinding("FILE-EDIT", "F4", "files"),
    KeyBinding("FILE-NEW-FOLDER", "F7", "files"),
    KeyBinding("TERM-COPY", "Ctrl+Shift+C", "terminal"),
    KeyBinding("TERM-PASTE", "Ctrl+Shift+V", "terminal"),
)


def bindings_for(platform: str) -> tuple[KeyBinding, ...]:
    """Return defaults for Windows/Linux; reject unsupported mechanical remaps."""
    normalized = platform.strip().lower()
    if normalized not in {"windows", "win32", "linux"}:
        raise ValueError(f"unsupported keymap platform: {platform}")
    return _COMMON


def conflicts(bindings: tuple[KeyBinding, ...]) -> tuple[tuple[KeyBinding, KeyBinding], ...]:
    result = []
    for index, left in enumerate(bindings):
        for right in bindings[index + 1 :]:
            if left.binding == right.binding and left.context == right.context and left.command_id != right.command_id:
                result.append((left, right))
    return tuple(result)

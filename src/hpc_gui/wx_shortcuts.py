"""Map user shortcut preferences onto wx accelerator entries (Qt parity).

The Qt shell honoured ``settings.shortcut_preferences`` for shell-level
commands; the wx shell used to hard-code F1.  This module turns the stored
bindings into ``(command_id, flags, keycode)`` triples without importing wx
at module import time, so the parsing stays unit-testable headless.
"""

from __future__ import annotations

from typing import Any, Iterable, Optional

SHELL_COMMANDS = ("APP-HELP", "APP-SETTINGS")

_NAMED_KEYS = {
    "enter": "WXK_RETURN", "return": "WXK_RETURN", "tab": "WXK_TAB",
    "delete": "WXK_DELETE", "del": "WXK_DELETE", "esc": "WXK_ESCAPE", "escape": "WXK_ESCAPE",
    "up": "WXK_UP", "down": "WXK_DOWN", "left": "WXK_LEFT", "right": "WXK_RIGHT",
    "home": "WXK_HOME", "end": "WXK_END", "pageup": "WXK_PAGEUP", "pagedown": "WXK_PAGEDOWN",
    "space": "WXK_SPACE", "backspace": "WXK_BACK", "insert": "WXK_INSERT",
}


def parse_binding(binding: str) -> Optional[tuple[frozenset[str], str]]:
    """``"Ctrl+Shift+N"`` -> ({"ctrl","shift"}, "N"); None when unparseable."""

    text = str(binding or "").strip()
    if not text:
        return None
    # A trailing "+" key ("Ctrl++") keeps its plus sign.
    parts = text[:-2].split("+") + ["+"] if text.endswith("++") else text.split("+")
    parts = [p.strip() for p in parts if p.strip()]
    if not parts:
        return None
    mods = set()
    for raw in parts[:-1]:
        low = raw.lower()
        if low in ("ctrl", "control", "cmd", "command", "meta"):
            mods.add("ctrl")  # wx maps ACCEL_CTRL to Cmd on macOS
        elif low in ("alt", "option", "opt"):
            mods.add("alt")
        elif low == "shift":
            mods.add("shift")
        else:
            return None
    return frozenset(mods), parts[-1]


def to_wx_accel(wx: Any, binding: str) -> Optional[tuple[int, int]]:
    parsed = parse_binding(binding)
    if parsed is None:
        return None
    mods, key = parsed
    flags = int(wx.ACCEL_NORMAL)
    if "ctrl" in mods:
        flags |= int(wx.ACCEL_CTRL)
    if "alt" in mods:
        flags |= int(wx.ACCEL_ALT)
    if "shift" in mods:
        flags |= int(wx.ACCEL_SHIFT)
    low = key.lower()
    if len(low) >= 2 and low[0] == "f" and low[1:].isdigit() and 1 <= int(low[1:]) <= 24:
        code = getattr(wx, f"WXK_F{int(low[1:])}", None)
    elif low in _NAMED_KEYS:
        code = getattr(wx, _NAMED_KEYS[low], None)
    elif len(key) == 1:
        code = ord(key.upper())
    else:
        return None
    return (flags, int(code)) if code is not None else None


def shell_bindings(platform: str, settings: Optional[dict] = None) -> list[tuple[str, str]]:
    """Active (command_id, binding) pairs for shell-context commands."""

    from hpc_gui.services.shortcut_preferences import ShortcutPreferences

    if settings is None:
        from hpc_gui.config.storage import load_settings

        settings = load_settings()
    prefs = ShortcutPreferences(platform, settings)
    result = [
        (item.command_id, item.binding)
        for item in prefs.bindings() if item.command_id in SHELL_COMMANDS
    ]
    # Keep Help ahead of Settings if both preferences target one accelerator.
    return sorted(result, key=lambda pair: 0 if pair[0] == "APP-HELP" else 1)


def shell_accelerators(wx: Any, bindings: Iterable[tuple[str, str]]) -> list[tuple[str, int, int]]:
    result = []
    seen = set()
    for command_id, binding in bindings:
        accel = to_wx_accel(wx, binding)
        if accel is None or accel in seen:
            continue
        seen.add(accel)
        result.append((command_id, accel[0], accel[1]))
    return result

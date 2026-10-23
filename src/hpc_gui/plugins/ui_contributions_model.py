"""Shared data model and limits for plugin-owned Plugins-menu contributions.

Framework-neutral leaf module: no Qt/wx imports and no internal dependencies.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping


# ---------------------------------------------------------------------------
# Limits and patterns
# ---------------------------------------------------------------------------

MAX_LABEL_LENGTH = 64
MAX_PLUGIN_ITEMS = 20
MAX_SUBMENU_ITEMS = 10
VALID_LABEL_RE = re.compile(r"^[^\n\r]+$")
ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$")
MAX_ID_LENGTH = 64

KNOWN_ACTION_KINDS = frozenset({"action", "submenu", "separator"})
KNOWN_CONDITION_KEYS = frozenset(
    {"connected", "disconnected", "editor_active", "file_selected", "plugin_enabled", "capability_available"}
)
VALID_UNAVAILABLE = frozenset({"disable", "hide"})

# Maximum nesting: Plugins -> plugin root -> optional subgroup -> action
# Within a plugin contribution, nesting is:
#   root items may be action / separator / submenu
#   submenu items may be action / separator only (no nested submenu)
MAX_NESTING_DEPTH = 1  # 0 = root, 1 = submenu


@dataclass(frozen=True)
class MenuContext:
    """Framework-neutral snapshot evaluated when the Plugins menu is about to open."""

    connected: bool = False
    editor_active: bool = False
    file_selected: bool = False
    language: str = "en"


@dataclass(frozen=True)
class PluginMenuAction:
    id: str
    label: str
    labels: Mapping[str, str]
    action: str
    when: Mapping[str, Any]
    unavailable: str  # "disable" | "hide"
    depth: int = 0


@dataclass(frozen=True)
class PluginMenuSeparator:
    id: str
    depth: int = 0


@dataclass(frozen=True)
class PluginMenuSubmenu:
    id: str
    label: str
    labels: Mapping[str, str]
    items: tuple[Any, ...]  # tuple[PluginMenuAction | PluginMenuSeparator]
    when: Mapping[str, Any]
    unavailable: str
    depth: int = 0


PluginMenuItem = PluginMenuAction | PluginMenuSeparator | PluginMenuSubmenu


@dataclass(frozen=True)
class PluginMenuContribution:
    """One plugin's validated contribution rooted under Plugins."""

    plugin_id: str
    plugin_version: str
    label: str
    labels: Mapping[str, str]
    items: tuple[PluginMenuItem, ...]  # normalized, order preserved

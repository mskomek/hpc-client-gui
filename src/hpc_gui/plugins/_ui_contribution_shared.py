from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Mapping
from hpc_gui.plugins.models import KNOWN_CAPABILITIES

logger = logging.getLogger(__name__)

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

MAX_NESTING_DEPTH = 1

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
    items: tuple[PluginMenuItem, ...]

def _is_valid_id(value: Any) -> bool:
    return isinstance(value, str) and 0 < len(value) <= MAX_ID_LENGTH and bool(ID_RE.fullmatch(value))

def _is_valid_label(value: Any) -> bool:
    return (
        isinstance(value, str)
        and value.strip()
        and len(value.strip()) <= MAX_LABEL_LENGTH
        and bool(VALID_LABEL_RE.fullmatch(value.strip()))
    )

def _validate_labels(raw: Any) -> tuple[dict[str, str], list[str]]:
    errors: list[str] = []
    result: dict[str, str] = {}
    if raw is None:
        return result, errors
    if not isinstance(raw, dict):
        errors.append("labels must be an object")
        return result, errors
    for key, value in raw.items():
        if not isinstance(key, str) or not key.strip():
            errors.append(f"labels key {key!r} must be a non-empty string")
            continue
        if not _is_valid_label(value):
            errors.append(f"labels[{key!r}] must be a non-empty string <= {MAX_LABEL_LENGTH}")
            continue
        result[str(key).strip()] = str(value).strip()
    return result, errors

def get_display_label(label: str, labels: Mapping[str, str] | None, language: str) -> str:
    """Return localized label with fallback to default label."""
    if labels and isinstance(labels, Mapping):
        loc = labels.get(language)
        if isinstance(loc, str) and loc.strip():
            if len(loc.strip()) <= MAX_LABEL_LENGTH:
                return loc.strip()
    return label

def _validate_when(raw: Any) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    if raw is None:
        return {}, errors
    if not isinstance(raw, dict):
        errors.append("when must be an object")
        return {}, errors
    result: dict[str, Any] = {}
    for key, value in raw.items():
        if key not in KNOWN_CONDITION_KEYS:
            logger.warning("Unknown condition key %r – will be treated as unsatisfied", key)
            errors.append(f"unknown condition {key!r}")
            # Still record as invalid so evaluation fails safely
            result[key] = value
            continue
        if key == "capability_available":
            if not isinstance(value, str) or not value.strip() or value not in KNOWN_CAPABILITIES:
                logger.warning("Invalid capability_available value %r", value)
                errors.append(f"capability_available must be a known capability, got {value!r}")
                result[key] = value
                continue
            result[key] = value.strip()
        else:
            if not isinstance(value, bool):
                logger.warning("Condition %r expected bool, got %r", key, type(value).__name__)
                errors.append(f"condition {key!r} must be a boolean")
                result[key] = value
                continue
            result[key] = value
    return result, errors

def evaluate_when(
    when: Mapping[str, Any] | None,
    context: MenuContext,
    capabilities: frozenset[str],
) -> bool:
    """Evaluate AND conditions. Invalid/unknown conditions fail safely (return False)."""
    if not when:
        return True
    for key, expected in when.items():
        if key not in KNOWN_CONDITION_KEYS:
            logger.warning("Unknown condition %r evaluated as not satisfied", key)
            return False
        if key == "capability_available":
            if not isinstance(expected, str):
                logger.warning("capability_available condition wrong type: %r", type(expected).__name__)
                return False
            if expected not in KNOWN_CAPABILITIES:
                logger.warning("capability_available unknown capability %r", expected)
                return False
            actual = expected in capabilities
            if not actual:
                return False
            continue
        if not isinstance(expected, bool):
            logger.warning("Condition %r has wrong type %r, expected bool", key, type(expected).__name__)
            return False
        if key == "connected":
            actual = context.connected
        elif key == "disconnected":
            actual = not context.connected
        elif key == "editor_active":
            actual = context.editor_active
        elif key == "file_selected":
            actual = context.file_selected
        elif key == "plugin_enabled":
            actual = True  # enabled plugins only enter evaluation; disabled are filtered earlier
        else:
            logger.warning("Unhandled condition %r", key)
            return False
        if actual != expected:
            return False
    return True

def _normalize_separators(items: tuple[PluginMenuItem, ...]) -> tuple[PluginMenuItem, ...]:
    """Remove leading/trailing and collapse consecutive separators, preserve order."""
    # Remove leading separators
    lst = list(items)
    while lst and isinstance(lst[0], PluginMenuSeparator):
        lst.pop(0)
    while lst and isinstance(lst[-1], PluginMenuSeparator):
        lst.pop()
    # Collapse consecutive
    normalized: list[PluginMenuItem] = []
    prev_was_sep = False
    for it in lst:
        is_sep = isinstance(it, PluginMenuSeparator)
        if is_sep and prev_was_sep:
            continue
        normalized.append(it)
        prev_was_sep = is_sep
    # For submenu inner items, we will call recursively but items are shallow so we don't need recursion here.
    return tuple(normalized)

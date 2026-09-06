"""Framework-neutral plugin-owned Plugins-menu contributions.

This module has no Qt/wx imports. It parses the declarative
``ui_contributions.plugins_menu`` payload that may appear in a manifest,
validates it conservatively, and evaluates ``when`` conditions against a
framework-neutral ``MenuContext`` snapshot.

A malformed single plugin contribution is skipped with a diagnostic and
must never crash startup or break other plugin menus.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Mapping

from hpc_gui.plugins.models import KNOWN_CAPABILITIES

logger = logging.getLogger(__name__)

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


def _parse_action(raw: Mapping[str, Any], depth: int, seen_ids: set[str], owning_id: str) -> tuple[PluginMenuAction | None, list[str]]:
    errors: list[str] = []
    item_id = raw.get("id")
    label = raw.get("label")
    action = raw.get("action")
    labels_raw = raw.get("labels")
    when_raw = raw.get("when")
    unavailable = raw.get("unavailable", "disable")

    if not _is_valid_id(item_id):
        errors.append(f"action id {item_id!r} must match {ID_RE.pattern}")
        return None, errors
    if item_id in seen_ids:
        errors.append(f"duplicate id {item_id!r} within plugin {owning_id}")
        return None, errors
    if not _is_valid_label(label):
        errors.append(f"action {item_id!r} label must be non-empty <= {MAX_LABEL_LENGTH}")
        return None, errors
    if not isinstance(action, str) or not action.strip():
        errors.append(f"action {item_id!r} requires a non-empty host action id")
        return None, errors
    # No plugin-defined shortcuts/icon paths allowed in this wave
    if "shortcut" in raw or "shortcuts" in raw or "keybinding" in raw or "accelerator" in raw:
        errors.append(f"action {item_id!r}: plugin-defined shortcuts are not allowed")
        return None, errors
    if "icon" in raw or "icon_path" in raw or "image" in raw:
        errors.append(f"action {item_id!r}: plugin-defined icons are not allowed")
        return None, errors

    labels, label_errors = _validate_labels(labels_raw)
    errors.extend(label_errors)
    when, when_errors = _validate_when(when_raw)
    # Unknown condition errors are logged but we still treat item as valid for evaluation fail-safe; however for
    # validation we want to allow unknown conditions to pass through as they will be disabled/hidden at eval time.
    # So we don't reject on when_errors unless it's malformed structure.
    # But we log them and keep the when for evaluation.
    # For now, ignore when_errors for rejection except structure errors.
    # We will filter when_errors that are truly invalid structure vs unknown condition.
    # Keep all when entries for evaluation.
    # So we don't append when_errors to errors for rejection (except if when itself not dict is already handled).

    if unavailable not in VALID_UNAVAILABLE:
        errors.append(f"action {item_id!r} unavailable must be 'disable' or 'hide'")
        return None, errors

    # Validate unexpected keys
    allowed_keys = {"kind", "id", "label", "labels", "action", "when", "unavailable"}
    extra = set(raw) - allowed_keys
    if extra:
        errors.append(f"action {item_id!r} has unknown properties {extra}")

    if errors:
        # If label errors etc exist, fail
        # But when_errors for unknown condition should not cause failure; we already handled.
        # So filter errors that are not from when unknown
        # Actually we already added when unknown to errors list but we want to not fail whole item for unknown condition.
        # Let's separate: if errors only contain unknown condition warnings, we should not reject.
        # Simpler: unknown condition should not be an error for validation rejection, just logged.
        # So we clear unknown-condition errors from rejection.
        filtered = [e for e in errors if not e.startswith("unknown condition") and not e.startswith("capability_available")]
        if filtered:
            return None, filtered
        # If only unknown condition issues, keep item but preserve raw when
        errors = []

    seen_ids.add(str(item_id))
    act = PluginMenuAction(
        id=str(item_id),
        label=str(label).strip(),
        labels=labels,
        action=str(action).strip(),
        when=when,
        unavailable=str(unavailable),
        depth=depth,
    )
    return act, []


def _parse_separator(raw: Mapping[str, Any], seen_ids: set[str], owning_id: str) -> tuple[PluginMenuSeparator | None, list[str]]:
    errors: list[str] = []
    item_id = raw.get("id")
    if not _is_valid_id(item_id):
        errors.append(f"separator id {item_id!r} must match {ID_RE.pattern}")
        return None, errors
    if item_id in seen_ids:
        errors.append(f"duplicate id {item_id!r} within plugin {owning_id}")
        return None, errors
    allowed_keys = {"kind", "id"}
    extra = set(raw) - allowed_keys
    if extra:
        errors.append(f"separator {item_id!r} has unknown properties {extra}")
        return None, errors
    seen_ids.add(str(item_id))
    return PluginMenuSeparator(id=str(item_id)), []


def _parse_submenu(
    raw: Mapping[str, Any], depth: int, seen_ids: set[str], owning_id: str
) -> tuple[PluginMenuSubmenu | None, list[str]]:
    errors: list[str] = []
    item_id = raw.get("id")
    label = raw.get("label")
    labels_raw = raw.get("labels")
    items_raw = raw.get("items")
    when_raw = raw.get("when")
    unavailable = raw.get("unavailable", "disable")

    if not _is_valid_id(item_id):
        errors.append(f"submenu id {item_id!r} must match {ID_RE.pattern}")
        return None, errors
    if item_id in seen_ids:
        errors.append(f"duplicate id {item_id!r} within plugin {owning_id}")
        return None, errors
    if not _is_valid_label(label):
        errors.append(f"submenu {item_id!r} label must be non-empty <= {MAX_LABEL_LENGTH}")
        return None, errors
    if not isinstance(items_raw, list):
        errors.append(f"submenu {item_id!r} requires an items list")
        return None, errors
    if len(items_raw) > MAX_SUBMENU_ITEMS:
        errors.append(f"submenu {item_id!r} exceeds max items {MAX_SUBMENU_ITEMS}")
        return None, errors
    if depth >= MAX_NESTING_DEPTH:
        errors.append(f"submenu {item_id!r} exceeds maximum nesting depth")
        return None, errors
    if "shortcut" in raw or "icon" in raw:
        errors.append(f"submenu {item_id!r}: shortcuts/icons not allowed")
        return None, errors

    labels, label_errors = _validate_labels(labels_raw)
    errors.extend(label_errors)
    when, _when_errors = _validate_when(when_raw)

    if unavailable not in VALID_UNAVAILABLE:
        errors.append(f"submenu {item_id!r} unavailable must be 'disable' or 'hide'")
        return None, errors

    allowed_keys = {"kind", "id", "label", "labels", "items", "when", "unavailable"}
    extra = set(raw) - allowed_keys
    if extra:
        errors.append(f"submenu {item_id!r} has unknown properties {extra}")
        return None, errors

    if errors:
        filtered = [e for e in errors if not e.startswith("unknown condition") and not e.startswith("capability_available")]
        if filtered:
            return None, filtered
        errors = []

    seen_ids.add(str(item_id))
    inner_items: list[PluginMenuItem] = []
    for idx, child_raw in enumerate(items_raw):
        if not isinstance(child_raw, dict):
            logger.warning("plugin %s submenu %s child %d is not an object – skipping", owning_id, item_id, idx)
            continue
        kind = child_raw.get("kind")
        if kind == "action":
            act, act_errors = _parse_action(child_raw, depth + 1, seen_ids, owning_id)
            if act_errors:
                logger.warning("plugin %s submenu %s child action %r invalid: %s", owning_id, item_id, child_raw.get("id"), "; ".join(act_errors))
                continue
            if act:
                inner_items.append(act)
        elif kind == "separator":
            sep, sep_errors = _parse_separator(child_raw, seen_ids, owning_id)
            if sep_errors:
                logger.warning("plugin %s submenu %s separator %r invalid: %s", owning_id, item_id, child_raw.get("id"), "; ".join(sep_errors))
                continue
            if sep:
                inner_items.append(sep)
        elif kind == "submenu":
            logger.warning("plugin %s submenu %s contains nested submenu %r – rejected (max nesting)", owning_id, item_id, child_raw.get("id"))
            continue
        else:
            logger.warning("plugin %s submenu %s child %r has invalid kind %r – skipping", owning_id, item_id, child_raw.get("id"), kind)
            continue

    # Normalize separators inside submenu
    inner_items = list(_normalize_separators(tuple(inner_items)))
    # Apply depth to inner items (ensure depth correct)
    adjusted: list[PluginMenuItem] = []
    for it in inner_items:
        if isinstance(it, PluginMenuAction):
            adjusted.append(PluginMenuAction(id=it.id, label=it.label, labels=it.labels, action=it.action, when=it.when, unavailable=it.unavailable, depth=depth+1))
        elif isinstance(it, PluginMenuSeparator):
            adjusted.append(PluginMenuSeparator(id=it.id, depth=depth+1))
        else:
            adjusted.append(it)
    when = when or {}
    sub = PluginMenuSubmenu(
        id=str(item_id),
        label=str(label).strip(),
        labels=labels,
        items=tuple(adjusted),
        when=when,
        unavailable=str(unavailable),
        depth=depth,
    )
    return sub, []


def _parse_plugins_menu(raw: Mapping[str, Any] | None, owning_id: str, version: str) -> tuple[PluginMenuContribution | None, list[str]]:
    if raw is None:
        return None, []
    if not isinstance(raw, dict):
        return None, ["plugins_menu must be an object"]
    label = raw.get("label")
    labels_raw = raw.get("labels")
    items_raw = raw.get("items")

    if not _is_valid_label(label):
        return None, [f"plugins_menu label must be non-empty <= {MAX_LABEL_LENGTH}"]
    if not isinstance(items_raw, list):
        return None, ["plugins_menu items must be a list"]
    if len(items_raw) > MAX_PLUGIN_ITEMS:
        return None, [f"plugins_menu exceeds max items {MAX_PLUGIN_ITEMS}"]
    if not items_raw:
        # Empty menu contributes nothing visibly but is valid opt-in? Treat as no items -> still contributes empty? We'll normalize to empty, but log.
        logger.info("plugin %s plugins_menu has no items", owning_id)

    labels, label_errors = _validate_labels(labels_raw)
    if label_errors:
        return None, label_errors

    allowed_keys = {"label", "labels", "items"}
    extra = set(raw) - allowed_keys
    if extra:
        return None, [f"plugins_menu has unknown properties {extra}"]

    seen_ids: set[str] = set()
    parsed_items: list[PluginMenuItem] = []
    for idx, item_raw in enumerate(items_raw):
        if not isinstance(item_raw, dict):
            logger.warning("plugin %s plugins_menu item %d is not an object – skipping", owning_id, idx)
            continue
        kind = item_raw.get("kind")
        if kind == "action":
            act, act_errors = _parse_action(item_raw, 0, seen_ids, owning_id)
            if act_errors:
                logger.warning("plugin %s action %r invalid: %s", owning_id, item_raw.get("id"), "; ".join(act_errors))
                continue
            if act:
                parsed_items.append(act)
        elif kind == "submenu":
            sub, sub_errors = _parse_submenu(item_raw, 0, seen_ids, owning_id)
            if sub_errors:
                logger.warning("plugin %s submenu %r invalid: %s", owning_id, item_raw.get("id"), "; ".join(sub_errors))
                continue
            if sub:
                parsed_items.append(sub)
        elif kind == "separator":
            sep, sep_errors = _parse_separator(item_raw, seen_ids, owning_id)
            if sep_errors:
                logger.warning("plugin %s separator %r invalid: %s", owning_id, item_raw.get("id"), "; ".join(sep_errors))
                continue
            if sep:
                parsed_items.append(sep)
        else:
            logger.warning("plugin %s plugins_menu item %r has invalid kind %r – skipping", owning_id, item_raw.get("id"), kind)
            continue

    # Normalize separators at top level
    parsed_items = list(_normalize_separators(tuple(parsed_items)))

    contribution = PluginMenuContribution(
        plugin_id=owning_id,
        plugin_version=version,
        label=str(label).strip(),
        labels=labels,
        items=tuple(parsed_items),
    )
    return contribution, []


def parse_ui_contributions(manifest_dict: Mapping[str, Any]) -> PluginMenuContribution | None:
    """Parse ui_contributions from a raw manifest dict. Returns contribution or None."""
    try:
        raw = manifest_dict.get("ui_contributions")
        if raw is None:
            return None
        if not isinstance(raw, dict):
            logger.warning("plugin %s ui_contributions is not an object – skipping", manifest_dict.get("id"))
            return None
        allowed_top = {"plugins_menu"}
        extra = set(raw) - allowed_top
        if extra:
            logger.warning("plugin %s ui_contributions has unknown properties %r – skipping", manifest_dict.get("id"), extra)
            return None
        plugins_menu_raw = raw.get("plugins_menu")
        if plugins_menu_raw is None:
            return None
        contribution, errors = _parse_plugins_menu(plugins_menu_raw, str(manifest_dict.get("id", "")), str(manifest_dict.get("version", "")))
        if errors:
            logger.warning("plugin %s plugins_menu validation failed: %s", manifest_dict.get("id"), "; ".join(errors))
            return None
        return contribution
    except Exception as exc:
        logger.warning("plugin %s ui_contributions parsing failed: %s", manifest_dict.get("id", ""), exc, exc_info=exc)
        return None


def validate_ui_contributions_dict(raw: Any) -> list[str]:
    """Validate ui_contributions dict for manifest validator. Returns errors."""
    errors: list[str] = []
    if not isinstance(raw, dict):
        return ["ui_contributions must be an object"]
    allowed_top = {"plugins_menu"}
    extra = set(raw) - allowed_top
    if extra:
        errors.append(f"ui_contributions has unknown properties {extra}")
        return errors
    plugins_menu = raw.get("plugins_menu")
    if plugins_menu is None:
        return ["ui_contributions must contain plugins_menu"]
    if not isinstance(plugins_menu, dict):
        errors.append("ui_contributions.plugins_menu must be an object")
        return errors
    label = plugins_menu.get("label")
    if not _is_valid_label(label):
        errors.append(f"plugins_menu label must be non-empty <= {MAX_LABEL_LENGTH}")
    labels_raw = plugins_menu.get("labels")
    if labels_raw is not None:
        _, label_errors = _validate_labels(labels_raw)
        errors.extend(label_errors)
    items_raw = plugins_menu.get("items")
    if not isinstance(items_raw, list):
        errors.append("plugins_menu items must be a list")
        return errors
    if len(items_raw) > MAX_PLUGIN_ITEMS:
        errors.append(f"plugins_menu exceeds max items {MAX_PLUGIN_ITEMS}")
    allowed_menu = {"label", "labels", "items"}
    extra2 = set(plugins_menu) - allowed_menu
    if extra2:
        errors.append(f"plugins_menu has unknown properties {extra2}")

    seen_ids: set[str] = set()
    for idx, item in enumerate(items_raw):
        if not isinstance(item, dict):
            errors.append(f"plugins_menu.items[{idx}] must be an object")
            continue
        kind = item.get("kind")
        if kind not in KNOWN_ACTION_KINDS:
            errors.append(f"plugins_menu.items[{idx}] has invalid kind {kind!r}")
            continue
        item_id = item.get("id")
        if not _is_valid_id(item_id):
            errors.append(f"plugins_menu.items[{idx}] id {item_id!r} must match {ID_RE.pattern}")
            continue
        if item_id in seen_ids:
            errors.append(f"duplicate id {item_id!r} within plugin contribution")
            continue
        seen_ids.add(str(item_id))
        if kind == "action":
            label2 = item.get("label")
            if not _is_valid_label(label2):
                errors.append(f"action {item_id!r} label must be non-empty <= {MAX_LABEL_LENGTH}")
            action = item.get("action")
            if not isinstance(action, str) or not action.strip():
                errors.append(f"action {item_id!r} requires a host action id")
            when_raw = item.get("when")
            if when_raw is not None:
                _, w_errs = _validate_when(when_raw)
                # For validator, unknown conditions are considered errors for strict schema? But spec says unknown must fail safely; validator should reject? We'll treat unknown as error for strict validation.
                if w_errs:
                    errors.extend(f"action {item_id!r}: {e}" for e in w_errs)
            unavailable = item.get("unavailable")
            if unavailable is not None and unavailable not in VALID_UNAVAILABLE:
                errors.append(f"action {item_id!r} unavailable must be 'disable' or 'hide'")
            extra_keys = set(item) - {"kind", "id", "label", "labels", "action", "when", "unavailable"}
            if extra_keys:
                errors.append(f"action {item_id!r} has unknown properties {extra_keys}")
            if "labels" in item:
                _, le = _validate_labels(item["labels"])
                errors.extend(f"action {item_id!r}: {e}" for e in le)
            if any(k in item for k in ("shortcut", "icon", "icon_path")):
                errors.append(f"action {item_id!r}: shortcuts/icons not allowed")
        elif kind == "separator":
            extra_keys = set(item) - {"kind", "id"}
            if extra_keys:
                errors.append(f"separator {item_id!r} has unknown properties {extra_keys}")
        elif kind == "submenu":
            label2 = item.get("label")
            if not _is_valid_label(label2):
                errors.append(f"submenu {item_id!r} label must be non-empty <= {MAX_LABEL_LENGTH}")
            inner = item.get("items")
            if not isinstance(inner, list):
                errors.append(f"submenu {item_id!r} requires items list")
                continue
            if len(inner) > MAX_SUBMENU_ITEMS:
                errors.append(f"submenu {item_id!r} exceeds max items {MAX_SUBMENU_ITEMS}")
            extra_keys = set(item) - {"kind", "id", "label", "labels", "items", "when", "unavailable"}
            if extra_keys:
                errors.append(f"submenu {item_id!r} has unknown properties {extra_keys}")
            if "labels" in item:
                _, le = _validate_labels(item["labels"])
                errors.extend(f"submenu {item_id!r}: {e}" for e in le)
            for j, child in enumerate(inner):
                if not isinstance(child, dict):
                    errors.append(f"submenu {item_id!r} child {j} must be object")
                    continue
                ck = child.get("kind")
                if ck not in {"action", "separator"}:
                    errors.append(f"submenu {item_id!r} child {j} has invalid kind {ck!r} (max nesting)")
                    continue
                cid = child.get("id")
                if not _is_valid_id(cid):
                    errors.append(f"submenu {item_id!r} child {j} id {cid!r} invalid")
                    continue
                if cid in seen_ids:
                    errors.append(f"duplicate id {cid!r} within plugin contribution")
                    continue
                seen_ids.add(str(cid))
                if ck == "action":
                    if not _is_valid_label(child.get("label")):
                        errors.append(f"submenu {item_id!r} action {cid!r} label invalid")
                    if not isinstance(child.get("action"), str) or not child.get("action").strip():
                        errors.append(f"submenu {item_id!r} action {cid!r} requires host action")
                    if "labels" in child:
                        _, le2 = _validate_labels(child["labels"])
                        errors.extend(le2)
                extra_child = set(child) - {"kind", "id", "label", "labels", "action", "when", "unavailable"}
                if ck == "separator":
                    extra_child = set(child) - {"kind", "id"}
                if extra_child:
                    errors.append(f"submenu {item_id!r} child {cid!r} has unknown properties {extra_child}")
                if any(k in child for k in ("shortcut", "icon", "icon_path")):
                    errors.append(f"submenu {item_id!r} child {cid!r}: shortcuts/icons not allowed")
    return errors


def collect_plugin_menu_contributions(installed_plugins) -> list[PluginMenuContribution]:
    """Collect valid contributions from installed plugins, deterministic ordering."""
    contributions: list[PluginMenuContribution] = []
    for plugin in sorted(installed_plugins, key=lambda p: p.manifest.id):
        try:
            raw_manifest = getattr(plugin.manifest, "ui_contributions", None)
            if raw_manifest is None:
                # Try to get from manifest if it was stored as dict in PluginManifest
                # The loader will have already parsed, but we also fallback to reading the
                # plugin directory's manifest.json if needed (defensive)
                continue
            # raw_manifest is expected to be dict with plugins_menu inside
            # But PluginManifest stores ui_contributions as mapping if present
            # We need to parse it: expect raw is the ui_contributions dict
            if isinstance(raw_manifest, dict) and "plugins_menu" in raw_manifest:
                # raw_manifest is the ui_contributions dict; parse its plugins_menu
                contrib, errs = _parse_plugins_menu(raw_manifest.get("plugins_menu"), plugin.manifest.id, plugin.manifest.version)
                if errs:
                    logger.warning("Skipping plugin %s contribution: %s", plugin.manifest.id, "; ".join(errs))
                    continue
                if contrib:
                    contributions.append(contrib)
            elif isinstance(raw_manifest, dict):
                # This could already be parsed contribution? Another path
                pass
            else:
                logger.warning("plugin %s ui_contributions unexpected type %r", plugin.manifest.id, type(raw_manifest))
        except Exception as exc:
            logger.warning("Failed to collect contribution for plugin %s: %s", getattr(plugin.manifest, "id", "?"), exc, exc_info=exc)
            continue
    # Alternative path: if PluginManifest.ui_contributions holds raw dict, above works.
    # Also handle case where InstalledPlugin has direct attribute contribution
    # Check for attribute plugin_contribution or similar
    # For now, also look for extra field stored on InstalledPlugin
    for plugin in installed_plugins:
        # Check if plugin has an already parsed attribute (future extension)
        alt = getattr(plugin, "plugin_menu_contribution", None)
        if isinstance(alt, PluginMenuContribution):
            if alt not in contributions:
                # dedup by plugin_id; sorting
                contributions = [c for c in contributions if c.plugin_id != alt.plugin_id]
                contributions.append(alt)
    contributions.sort(key=lambda c: c.plugin_id)
    return contributions


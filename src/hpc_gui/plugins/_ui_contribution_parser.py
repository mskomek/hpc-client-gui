from __future__ import annotations

import logging
from typing import Any, Mapping

from hpc_gui.plugins._ui_contribution_shared import (
    ID_RE, MAX_LABEL_LENGTH, MAX_NESTING_DEPTH,
    MAX_PLUGIN_ITEMS, MAX_SUBMENU_ITEMS, VALID_UNAVAILABLE, PluginMenuAction,
    PluginMenuContribution, PluginMenuItem, PluginMenuSeparator, PluginMenuSubmenu,
    _is_valid_id, _is_valid_label, _normalize_separators, _validate_labels, _validate_when,
)

logger = logging.getLogger(__name__)

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
    if when_errors:
        for werr in when_errors:
            logger.warning("plugin %s action %r invalid when %r: %s", owning_id, item_id, when_raw, werr)
        return None, when_errors

    if unavailable not in VALID_UNAVAILABLE:
        errors.append(f"action {item_id!r} unavailable must be 'disable' or 'hide'")
        return None, errors

    # Validate unexpected keys
    allowed_keys = {"kind", "id", "label", "labels", "action", "when", "unavailable"}
    extra = set(raw) - allowed_keys
    if extra:
        errors.append(f"action {item_id!r} has unknown properties {extra}")

    if errors:
        return None, errors

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
    when, when_errors = _validate_when(when_raw)
    if when_errors:
        for werr in when_errors:
            logger.warning("plugin %s submenu %r invalid when %r: %s", owning_id, item_id, when_raw, werr)
        return None, when_errors

    if unavailable not in VALID_UNAVAILABLE:
        errors.append(f"submenu {item_id!r} unavailable must be 'disable' or 'hide'")
        return None, errors

    allowed_keys = {"kind", "id", "label", "labels", "items", "when", "unavailable"}
    extra = set(raw) - allowed_keys
    if extra:
        errors.append(f"submenu {item_id!r} has unknown properties {extra}")
        return None, errors

    if errors:
        return None, errors

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

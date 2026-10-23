"""Plugins-menu manifest parsing for plugin menu contributions."""

from __future__ import annotations

import logging
from typing import Any, Mapping

from hpc_gui.plugins.ui_contributions_items import (
    _normalize_separators,
    _parse_action,
    _parse_separator,
    _parse_submenu,
)
from hpc_gui.plugins.ui_contributions_model import (
    MAX_LABEL_LENGTH,
    MAX_PLUGIN_ITEMS,
    PluginMenuContribution,
    PluginMenuItem,
)
from hpc_gui.plugins.ui_contributions_primitives import _is_valid_label, _validate_labels

logger = logging.getLogger(__name__)


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

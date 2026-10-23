"""Manifest-level validation of ``ui_contributions`` payloads."""

from __future__ import annotations

from typing import Any

from hpc_gui.plugins.ui_contributions_conditions import _validate_when
from hpc_gui.plugins.ui_contributions_model import (
    ID_RE,
    KNOWN_ACTION_KINDS,
    MAX_LABEL_LENGTH,
    MAX_PLUGIN_ITEMS,
    MAX_SUBMENU_ITEMS,
    VALID_UNAVAILABLE,
)
from hpc_gui.plugins.ui_contributions_primitives import (
    _is_valid_id,
    _is_valid_label,
    _validate_labels,
)


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

"""``when`` condition validation and evaluation for plugin menu contributions."""

from __future__ import annotations

import logging
from typing import Any, Mapping

from hpc_gui.plugins.models import KNOWN_CAPABILITIES
from hpc_gui.plugins.ui_contributions_model import KNOWN_CONDITION_KEYS, MenuContext

logger = logging.getLogger(__name__)


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

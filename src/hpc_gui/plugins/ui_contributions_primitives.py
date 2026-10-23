"""Identifier, label and localized-label primitives for plugin menu contributions."""

from __future__ import annotations

from typing import Any, Mapping

from hpc_gui.plugins.ui_contributions_model import (
    ID_RE,
    MAX_ID_LENGTH,
    MAX_LABEL_LENGTH,
    VALID_LABEL_RE,
)


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

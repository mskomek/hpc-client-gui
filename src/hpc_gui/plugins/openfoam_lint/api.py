"""Compatibility facade for the canonical host-owned OpenFOAM linter API.

The implementation lives in ``hpc_gui.plugin_engines.openfoam_lint.api``.
This module only preserves the API-1 diagnostic shape used by old rule
consumers; it contains no parser, size policy, filesystem traversal, or lint
rules of its own.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from hpc_gui.openfoam_core.limits import MAX_TEXT_BYTES

MAX_INPUT_BYTES = MAX_TEXT_BYTES


@dataclass(frozen=True)
class Diagnostic:
    """Legacy view of a canonical diagnostic for API-1 callers."""

    rule: str
    severity: str
    certainty: str
    file: str
    line: int
    column: int
    message: str
    fix_preview: str = ""


def _legacy(items) -> list[Diagnostic]:
    return [
        Diagnostic(
            rule=item.rule_id,
            severity=item.severity,
            certainty=item.confidence,
            file=item.path,
            line=item.line,
            column=item.column,
            message=item.message,
            fix_preview=item.suggested_fix,
        )
        for item in items
    ]


def lint_text(relpath: str, text: str, *, release: str | None = None) -> list[Diagnostic]:
    """Delegate text linting to the single canonical static engine."""
    from hpc_gui.plugin_engines.openfoam_lint.api import lint_text as canonical_lint_text

    return _legacy(canonical_lint_text(text, file_name=relpath, release=release).diagnostics)


def lint_paths(paths, options=None, *, release: str | None = None) -> list[Diagnostic]:
    """Delegate bounded file/case reads and linting to the canonical engine."""
    from hpc_gui.plugin_engines.openfoam_lint.api import lint_paths as canonical_lint_paths

    return _legacy(canonical_lint_paths(paths, options=options, release=release).diagnostics)


def read_text_limited(path: str) -> str:
    """Read a bounded UTF-8 dictionary without following links."""
    from hpc_gui.openfoam_core import MAX_DICTIONARY_BYTES, read_dictionary_file

    payload = read_dictionary_file(Path(path))
    if len(payload.data) > MAX_DICTIONARY_BYTES:
        raise ValueError("dictionary exceeds the configured size limit")
    try:
        return payload.data.decode("utf-8", errors="strict")
    except UnicodeError as exc:
        raise ValueError("dictionary is not valid UTF-8") from exc


def rule_catalog() -> list[dict[str, str]]:
    """Expose canonical rule metadata in the legacy list-shaped form."""
    from hpc_gui.plugin_engines.openfoam_lint.api import rule_catalog as canonical_rule_catalog

    catalog = canonical_rule_catalog()
    return [
        {
            "id": rule_id,
            "family": "-".join(rule_id.split("-")[:2]),
            "severity": metadata.get("severity", "warning"),
        }
        for rule_id, metadata in sorted(catalog.items())
    ]

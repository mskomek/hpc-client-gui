"""Pure, testable lint evaluation over declarative rule packs.

No Qt dependency, no code execution: rules are constrained primitives
compiled to regexes at pack-load time.
"""

from __future__ import annotations

import re

from hpc_gui.lint.models import Diagnostic, LintContext, RulePack, Severity

# Resource limits (constants so tests can pin them).
MAX_LINT_TEXT_BYTES = 10 * 1024 * 1024
DEFAULT_MAX_DIAGNOSTICS_PER_RULE = 100
DEFAULT_MAX_DIAGNOSTICS_TOTAL = 500


class LintError(ValueError):
    """Raised for oversized input or unusable rule packs."""


class _LineIndex:
    __slots__ = ("_offsets", "_length")

    def __init__(self, text: str) -> None:
        self._offsets = [0]
        for match in re.finditer("\n", text):
            self._offsets.append(match.end())
        self._length = len(text)

    def position(self, offset: int) -> tuple[int, int]:
        """Return (1-based line, 1-based column) for a character offset."""
        offset = max(0, min(offset, self._length))
        low, high = 0, len(self._offsets) - 1
        while low < high:
            mid = (low + high + 1) // 2
            if self._offsets[mid] <= offset:
                low = mid
            else:
                high = mid - 1
        return low + 1, offset - self._offsets[low] + 1


def _target_version_matches(when: dict, context: LintContext | None) -> bool:
    target = when.get("target_version")
    if not target:
        return True
    if context is None or not context.application_version:
        return False
    current = context.application_version
    if target.endswith(".*"):
        return current.startswith(target[:-1])
    return current == target or current.startswith(target + ".")


def _iter_rule_diagnostics(
    text: str,
    index: _LineIndex,
    rule,
    pack: RulePack,
    context: LintContext | None,
    per_rule_cap: int,
):
    kind = rule.kind
    severity = Severity(rule.severity)

    def diagnostic(line=None, column=None) -> Diagnostic:
        target_version = str(rule.when.get("target_version", "")) if rule.when else ""
        return Diagnostic(
            rule_id=rule.id,
            severity=severity,
            message=rule.message,
            category=rule.category,
            source=pack.linter_id,
            line=line,
            column=column,
            plugin_id=pack.plugin_id,
            plugin_version=pack.plugin_version,
            target_version=target_version,
            explanation=rule.explanation,
            suggested_fix=rule.suggested_fix,
            documentation_url=rule.documentation_url,
        )

    emitted = 0
    if kind == "contains":
        value = rule.values[0] if rule.values else ""
        if value and value not in text:
            yield diagnostic()
        return
    if kind == "not_contains":
        value = rule.values[0] if rule.values else ""
        if value and value in text:
            start = text.find(value)
            line, column = index.position(start)
            yield diagnostic(line, column)
        return
    if kind == "regex":
        pattern = re.compile(rule.values[0]) if rule.values else None
        if pattern is None:
            return
        count = 0
        for match in pattern.finditer(text):
            line, column = index.position(match.start())
            yield diagnostic(line, column)
            count += 1
            emitted += 1
            if emitted >= per_rule_cap:
                break
        _ = count
        return
    if kind == "line_regex":
        pattern = re.compile(rule.values[0]) if rule.values else None
        if pattern is None:
            return
        for line_number, line_text in enumerate(text.splitlines(), start=1):
            match = pattern.search(line_text)
            if match:
                yield diagnostic(line_number, match.start() + 1)
                emitted += 1
                if emitted >= per_rule_cap:
                    break
        return
    if kind == "ordered_patterns":
        cursor = 0
        last_line = last_column = None
        in_order = True
        for value in rule.values:
            found = text.find(value, cursor)
            if found < 0:
                in_order = False
                break
            last_line, last_column = index.position(found)
            cursor = found + len(value)
        if not in_order and rule.values:
            yield diagnostic(last_line, last_column)
        return
    if kind == "count":
        value = rule.values[0] if rule.values else ""
        occurrences = text.count(value) if value else 0
        minimum = rule.min_count if rule.min_count is not None else 1
        maximum = rule.max_count
        if occurrences < minimum or (maximum is not None and occurrences > maximum):
            yield diagnostic()
        return
    # Unknown kinds are rejected at load time; ignore defensively here.
    return


def lint_text(
    text: str,
    *,
    file_name: str,
    rule_pack: RulePack,
    context: LintContext | None = None,
    max_diagnostics_per_rule: int = DEFAULT_MAX_DIAGNOSTICS_PER_RULE,
    max_diagnostics_total: int = DEFAULT_MAX_DIAGNOSTICS_TOTAL,
) -> list[Diagnostic]:
    """Evaluate one rule pack against text; returns sorted diagnostics."""
    _ = file_name  # matching is the caller's concern; kept for API symmetry
    encoded_size = len(text.encode("utf-8", errors="replace"))
    if encoded_size > MAX_LINT_TEXT_BYTES:
        raise LintError("Input exceeds the maximum lint size.")

    index = _LineIndex(text)
    diagnostics: list[Diagnostic] = []
    for rule in rule_pack.rules:
        if not _target_version_matches(rule.when, context):
            continue
        for diagnostic in _iter_rule_diagnostics(
            text, index, rule, rule_pack, context, max_diagnostics_per_rule
        ):
            diagnostics.append(diagnostic)
            if len(diagnostics) >= max_diagnostics_total:
                return sorted(
                    diagnostics,
                    key=lambda d: (d.line or 0, d.column or 0, d.rule_id),
                )
    return sorted(diagnostics, key=lambda d: (d.line or 0, d.column or 0, d.rule_id))

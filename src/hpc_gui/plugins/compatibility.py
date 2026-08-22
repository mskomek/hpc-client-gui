"""Small, fail-closed ``requires_app`` compatibility checker.

Supported subset (Plugin API v1):

    ">=1.4.0"
    ">=1.4.0,<2.0.0"
    "==1.4.*"
    ">1.4.0", "<2.0.0", "<=2.0.0"

Any other syntax fails closed (incompatible). No third-party dependency is
used so packaged builds stay lean.
"""

from __future__ import annotations

import re

_CLAUSE_RE = re.compile(r"^(>=|<=|==|~=|>|<)?(\d+)(?:\.(\d+|\*))?(?:\.(\d+|\*))?$")


def parse_version(value: str) -> tuple[int, ...] | None:
    """Parse a concrete semantic-ish version into a comparable tuple."""
    if not isinstance(value, str):
        return None
    core = value.split("+", 1)[0].split("-", 1)[0]
    parts = core.split(".")
    numbers: list[int] = []
    for part in parts:
        if not part.isdigit():
            return None
        numbers.append(int(part))
    while len(numbers) < 3:
        numbers.append(0)
    return tuple(numbers)


def _parse_clauses(requires_app: str) -> list[tuple[str, str]]:
    clauses: list[tuple[str, str]] = []
    for raw_clause in requires_app.split(","):
        clause = raw_clause.strip()
        if not clause:
            raise ValueError("requires_app contains an empty version clause")
        match = _CLAUSE_RE.fullmatch(clause)
        if match is None:
            raise ValueError(f"unsupported requires_app clause: {clause!r}")
        operator = match.group(1) or "=="
        clauses.append((operator, clause[len(match.group(1) or "") :]))
    return clauses


def _compare(left: tuple[int, ...], right: tuple[int, ...]) -> int:
    for a, b in zip(left, right):
        if a != b:
            return -1 if a < b else 1
    return 0


def validate_requires_app(requires_app: str) -> list[str]:
    """Return a list of human-readable problems; empty means supported."""
    errors: list[str] = []
    try:
        clauses = _parse_clauses(requires_app)
    except ValueError as exc:
        return [str(exc)]
    if not clauses:
        errors.append("requires_app must contain at least one version clause")
    for operator, version_text in clauses:
        if "*" in version_text and operator != "==":
            errors.append(f"wildcards are only supported with '==': {operator}{version_text}")
        if operator == "~=" and version_text.count(".") < 1:
            errors.append(f"'~=' needs at least two components: ~={version_text}")
    return errors


def is_app_compatible(requires_app: str, app_version: str) -> bool:
    """Fail-closed compatibility check of ``requires_app`` against the app."""
    errors = validate_requires_app(requires_app)
    if errors:
        return False
    current = parse_version(app_version)
    if current is None:
        return False
    try:
        clauses = _parse_clauses(requires_app)
    except ValueError:
        return False
    for operator, version_text in clauses:
        if "*" in version_text:
            prefix = tuple(int(part) for part in version_text.rstrip("*").rstrip(".").split("."))
            if _compare(current[: len(prefix)], prefix) != 0:
                return False
            continue
        target = parse_version(version_text)
        if target is None:
            return False
        order = _compare(current, target)
        if operator == ">=" and order < 0:
            return False
        if operator == ">" and order <= 0:
            return False
        if operator == "<=" and order > 0:
            return False
        if operator == "<" and order >= 0:
            return False
        if operator == "==" and order != 0:
            return False
        if operator == "~=":
            prefix_length = max(1, len(target) - 1)
            if order < 0 or _compare(current[:prefix_length], target[:prefix_length]) != 0:
                return False
    return True

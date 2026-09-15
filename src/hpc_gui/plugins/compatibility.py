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


def _bump_last(version: tuple[int, ...]) -> tuple[int, ...]:
    return version[:-1] + (version[-1] + 1,)


def minimum_admitted_version(requires_app: str) -> tuple[int, ...] | None:
    """Lowest version the range admits, as a comparable tuple.

    Returns ``None`` when the range is invalid or uses syntax outside the
    supported subset. A range with no lower bound (for example ``<2.0.0``)
    admits arbitrarily old releases and returns ``(0, 0, 0)``.
    """
    if validate_requires_app(requires_app):
        return None
    try:
        clauses = _parse_clauses(requires_app)
    except ValueError:
        return None
    floor: tuple[int, ...] | None = None
    for operator, version_text in clauses:
        if "*" in version_text:
            prefix = tuple(
                int(part) for part in version_text.rstrip("*").rstrip(".").split(".")
            )
            candidate = prefix + (0,) * max(0, 3 - len(prefix))
        else:
            candidate = parse_version(version_text)
            if candidate is None:
                return None
        if operator in (">=", ">", "==", "~="):
            if operator == ">":
                candidate = _bump_last(candidate)
            if floor is None or _compare(candidate, floor) > 0:
                floor = candidate
    return floor if floor is not None else (0, 0, 0)


def maximum_admitted_version(requires_app: str) -> tuple[int, ...] | None:
    """Highest version the range admits, or ``None`` for no upper bound.

    Invalid ranges also return ``None``; callers that need to tell the two
    apart validate the range first.
    """
    if validate_requires_app(requires_app):
        return None
    try:
        clauses = _parse_clauses(requires_app)
    except ValueError:
        return None
    ceiling: tuple[int, ...] | None = None
    for operator, version_text in clauses:
        if "*" in version_text:
            # "==1.4.*" admits everything below the next prefix.
            prefix = tuple(
                int(part) for part in version_text.rstrip("*").rstrip(".").split(".")
            )
            candidate = _bump_last(prefix) + (0,) * max(0, 3 - len(prefix))
        else:
            parsed = parse_version(version_text)
            if parsed is None:
                return None
            candidate = parsed
        if operator in ("<", "<=", "==", "~="):
            if operator == "~=":
                prefix_length = max(1, len(candidate) - 1)
                candidate = _bump_last(candidate[:prefix_length]) + (0,) * (
                    3 - prefix_length
                )
            if ceiling is None or _compare(candidate, ceiling) < 0:
                ceiling = candidate
    return ceiling


# --- Registry-level compatibility override --------------------------------
#
# A published plugin package's bytes are immutable, so a compatibility
# mistake found after publication is corrected in the registry instead:
#
#   "compatibility_override": {
#     "requires_app": ">=1.6.0", "reason": "...", "recorded": "2026-09-15"
#   }
#
# The application is a separate trust boundary from the registry and
# validates the field itself. An override may only NARROW compatibility, and
# it governs registry-level decisions only - discovery, offerability, and
# version resolution. The downloaded immutable manifest stays the installer's
# authority, and cluster-profile schema capability stays an independent
# fail-closed boundary, so an override can never widen what actually
# installs.

_RECORDED_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def validate_compatibility_override(entry: object) -> list[str]:
    """Problems with a registry entry's optional ``compatibility_override``.

    An entry without the field is valid: registries published before the
    field existed must keep working unchanged.
    """
    if not isinstance(entry, dict):
        return ["registry entry must be a JSON object"]
    override = entry.get("compatibility_override")
    if override is None:
        return []
    if not isinstance(override, dict):
        return ["compatibility_override must be a JSON object"]

    errors: list[str] = []
    allowed = {"requires_app", "reason", "recorded"}
    unknown = sorted(set(override) - allowed)
    if unknown:
        errors.append(
            "compatibility_override has unsupported key(s): " + ", ".join(unknown)
        )

    override_range = override.get("requires_app")
    if not isinstance(override_range, str) or not override_range.strip():
        errors.append("compatibility_override.requires_app must be a non-empty string")
        override_range = None
    else:
        errors.extend(
            f"compatibility_override.{problem}"
            for problem in validate_requires_app(override_range)
        )

    reason = override.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        errors.append("compatibility_override.reason must be a non-empty string")

    recorded = override.get("recorded")
    if recorded is not None and (
        not isinstance(recorded, str) or not _RECORDED_RE.fullmatch(recorded)
    ):
        errors.append("compatibility_override.recorded must be an ISO date (YYYY-MM-DD)")

    declared = entry.get("requires_app")
    if override_range is not None and isinstance(declared, str) and not errors:
        errors.extend(_widening_errors(declared, override_range))
    return errors


def _widening_errors(declared: str, override_range: str) -> list[str]:
    """Reject an override that admits anything the published range rejects."""
    if validate_requires_app(declared):
        # The published range is itself invalid; that is reported separately.
        return []
    declared_floor = minimum_admitted_version(declared)
    override_floor = minimum_admitted_version(override_range)
    if declared_floor is None or override_floor is None:
        return [
            f"compatibility_override.requires_app {override_range!r} cannot be "
            f"compared with the published requires_app {declared!r}"
        ]
    problem = (
        f"compatibility_override.requires_app {override_range!r} would admit "
        f"releases the published requires_app {declared!r} does not; an "
        f"override may only narrow compatibility"
    )
    if _compare(override_floor, declared_floor) < 0:
        return [problem]
    declared_ceiling = maximum_admitted_version(declared)
    if declared_ceiling is not None:
        override_ceiling = maximum_admitted_version(override_range)
        if override_ceiling is None or _compare(override_ceiling, declared_ceiling) > 0:
            return [problem]
    return []


def effective_requires_app(entry: object) -> str | None:
    """The range the registry actually advertises for ``entry``.

    Returns the published ``requires_app`` when there is no override, the
    override's range when the override is valid, and ``None`` when the entry
    or its override is malformed. ``None`` means "undecidable": callers treat
    it as incompatible rather than falling back to the wider published range.
    """
    if not isinstance(entry, dict):
        return None
    declared = entry.get("requires_app")
    if not isinstance(declared, str):
        return None
    if validate_compatibility_override(entry):
        return None
    override = entry.get("compatibility_override")
    if isinstance(override, dict):
        override_range = override.get("requires_app")
        if isinstance(override_range, str) and override_range.strip():
            return override_range
    return declared


def entry_is_app_compatible(entry: object, app_version: str) -> bool:
    """Fail-closed registry-level compatibility check for one entry.

    This is the single application-side answer to "may this release be
    offered this registry entry?". Every registry-level decision - discovery,
    latest-compatible resolution, Plugin Manager offerability, install
    prechecks - goes through here so the override cannot be honoured in one
    place and ignored in another.
    """
    effective = effective_requires_app(entry)
    if effective is None:
        return False
    return is_app_compatible(effective, app_version)


__all__ = [
    "effective_requires_app",
    "entry_is_app_compatible",
    "is_app_compatible",
    "maximum_admitted_version",
    "minimum_admitted_version",
    "parse_version",
    "validate_compatibility_override",
    "validate_requires_app",
]

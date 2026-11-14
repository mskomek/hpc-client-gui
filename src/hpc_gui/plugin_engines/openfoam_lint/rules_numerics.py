"""Cross-file solver/numerics consistency checks (W65 LINT-013).

Only static, source-backed relationships are reported: a solver family that
requires a steady or transient time scheme against the parsed
ddtSchemes/default entry. Unlisted solvers and dynamic entries are left alone
so the rule cannot invent a mismatch.
"""
from __future__ import annotations

import re

from hpc_gui.openfoam_core import (
    Diagnostic,
    ParsedDictionary,
    SOURCE_DOCS,
    time_treatment_for,
)

_REGION_SCHEMES = re.compile(r"^(?P<prefix>.+/)?system/(?P<region>[^/]+)/fvSchemes$")


def _single_value(parsed: ParsedDictionary, key: str, scope: tuple[str, ...] = ()) -> str | None:
    entries = parsed.find(key, scope)
    if len(entries) != 1:
        return None
    entry = entries[0]
    if entry.dynamic:
        return None
    return entry.value.strip()


def lint_solver_scheme_consistency(
    parsed_files: dict[str, ParsedDictionary],
) -> tuple[Diagnostic, ...]:
    """Report a steady/transient time-scheme mismatch for known solvers."""
    control_paths = [
        path for path in parsed_files
        if path == "system/controlDict" or path.endswith("/system/controlDict")
    ]
    if len(control_paths) != 1:
        return ()
    solver = _single_value(parsed_files[control_paths[0]], "application")
    treatment = time_treatment_for(solver) if solver else None
    if treatment is None:
        return ()
    schemes_paths = [
        path for path in parsed_files
        if path == "system/fvSchemes" or path.endswith("/system/fvSchemes")
    ]
    if len(schemes_paths) > 1:
        return ()
    findings: list[Diagnostic] = []
    if schemes_paths:
        root = _mismatch_finding(
            schemes_paths[0], parsed_files[schemes_paths[0]], solver, treatment, "",
        )
        if root is not None:
            findings.append(root)
    findings.extend(_region_scheme_findings(parsed_files, solver, treatment))
    return tuple(findings)


def _mismatch_finding(
    path: str,
    parsed: ParsedDictionary,
    solver: str,
    treatment: str,
    region_note: str,
) -> Diagnostic | None:
    scheme = _single_value(parsed, "default", ("ddtSchemes",))
    if scheme is None:
        return None
    if treatment == "steady" and scheme != "steadyState":
        message = f"{solver} requires ddtSchemes default steadyState.{region_note}"
    elif treatment == "transient" and scheme == "steadyState":
        message = (
            f"{solver} is a transient solver; ddtSchemes default steadyState is not valid."
            f"{region_note}"
        )
    else:
        return None
    entry = parsed.find("default", ("ddtSchemes",))[0]
    return Diagnostic(
        "OF-NUM-010", "error", "definite", path, entry.line, entry.column,
        message,
        "Set ddtSchemes default to a scheme matching the solver's steady or transient nature.",
        SOURCE_DOCS, verification_level="static",
    )


def _region_scheme_findings(
    parsed_files: dict[str, ParsedDictionary],
    solver: str,
    treatment: str,
) -> tuple[Diagnostic, ...]:
    """Check per-region fvSchemes; runs alongside a root-level file (CHT)."""
    findings: list[Diagnostic] = []
    for path in sorted(parsed_files):
        match = _REGION_SCHEMES.match(path)
        if match is None:
            continue
        note = f" (region {match.group('region')})"
        finding = _mismatch_finding(path, parsed_files[path], solver, treatment, note)
        if finding is not None:
            findings.append(finding)
    return tuple(findings)

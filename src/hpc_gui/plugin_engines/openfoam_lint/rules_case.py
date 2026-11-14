"""Cross-file and case-layout checks with conservative confidence labels."""
from __future__ import annotations

import math
from pathlib import PurePosixPath

from hpc_gui.openfoam_core import (
    Diagnostic, Entry, ParsedDictionary, SOURCE_DOCS, parse_region_properties,
)
from .rules_solver_fields import lint_solver_fields


def _first(parsed: ParsedDictionary | None, key: str, scope: tuple[str, ...] = ()) -> str | None:
    if parsed is None:
        return None
    value = parsed.value(key, scope=scope)
    return value.strip().strip('"\'') if isinstance(value, str) else None


def _static_number(parsed: ParsedDictionary, key: str) -> tuple[float, Entry] | None:
    matches = parsed.find(key, scope=())
    if len(matches) != 1:
        return None
    entry = matches[0]
    if entry.dynamic or len(entry.value_tokens) != 1 or entry.value_tokens[0].kind != "atom":
        return None
    try:
        value = float(entry.value_tokens[0].value)
    except ValueError:
        return None
    if not math.isfinite(value):
        return None
    return value, entry


def _parallel_layout_check(decompose: ParsedDictionary) -> list[Diagnostic]:
    """Check explicit Cartesian splits without interpreting dynamic dictionaries."""
    counts = decompose.find("numberOfSubdomains", scope=())
    methods = decompose.find("method", scope=())
    if len(counts) != 1 or len(methods) != 1:
        return []
    count_entry, method_entry = counts[0], methods[0]
    if (
        count_entry.dynamic or count_entry.is_dictionary
        or len(count_entry.value_tokens) != 1 or count_entry.value_tokens[0].kind != "atom"
        or method_entry.dynamic or method_entry.is_dictionary
        or len(method_entry.value_tokens) != 1 or method_entry.value_tokens[0].kind != "atom"
    ):
        return []
    try:
        count = int(count_entry.value_tokens[0].value)
    except ValueError:
        return []
    method = method_entry.value_tokens[0].value
    if count <= 0 or method not in {"simple", "hierarchical"}:
        return []

    candidates = ("coeffs", f"{method}Coeffs")
    candidate_entries = [decompose.find("n", scope=(name,)) for name in candidates]
    populated = [entries for entries in candidate_entries if entries]
    if len(populated) != 1 or len(populated[0]) != 1:
        return []
    entry = populated[0][0]
    if entry.dynamic:
        return []
    tokens = entry.value_tokens
    valid_shape = (
        len(tokens) == 5
        and tokens[0].value == "("
        and tokens[-1].value == ")"
        and all(token.kind == "atom" for token in tokens[1:-1])
    )
    try:
        dimensions = [int(token.value) for token in tokens[1:-1]] if valid_shape else []
    except ValueError:
        dimensions = []
    if len(dimensions) != 3 or any(value <= 0 for value in dimensions):
        message = (
            "Static Cartesian decomposition n must contain three positive integer dimensions."
        )
    elif math.prod(dimensions) != count:
        message = (
            f"Cartesian decomposition n multiplies to {math.prod(dimensions)}, "
            f"but numberOfSubdomains is {count}."
        )
    else:
        return []
    return [Diagnostic(
        "OF-PAR-002", "warning", "structural", "system/decomposeParDict",
        entry.line, entry.column, message,
        "Set three positive Cartesian dimensions whose product equals numberOfSubdomains; "
        "dynamic or ambiguous entries are not checked.", SOURCE_DOCS, verification_level="static",
    )]


def _control_time_checks(control: ParsedDictionary | None) -> list[Diagnostic]:
    if control is None:
        return []
    findings: list[Diagnostic] = []
    start = _static_number(control, "startTime")
    end = _static_number(control, "endTime")
    if start is not None and end is not None and end[0] < start[0]:
        entry = end[1]
        findings.append(Diagnostic(
            "OF-CTRL-001", "warning", "structural", "system/controlDict", entry.line, entry.column,
            "Static endTime is earlier than static startTime.",
            "Set endTime to a value at or after startTime; dynamic values are not checked.",
            SOURCE_DOCS, verification_level="static",
        ))
    delta_t = _static_number(control, "deltaT")
    if delta_t is not None and delta_t[0] <= 0:
        entry = delta_t[1]
        findings.append(Diagnostic(
            "OF-CTRL-002", "warning", "structural", "system/controlDict", entry.line, entry.column,
            "Static deltaT must be positive.",
            "Set a positive finite value or review the dynamic expression manually.",
            SOURCE_DOCS, verification_level="static",
        ))
    write_control = _first(control, "writeControl")
    if write_control in {"timeStep", "runTime", "adjustableRunTime", "cpuTime", "clockTime"}:
        interval = _static_number(control, "writeInterval")
        if interval is not None and interval[0] <= 0:
            entry = interval[1]
            findings.append(Diagnostic(
                "OF-CTRL-003", "warning", "structural", "system/controlDict", entry.line, entry.column,
                "Static writeInterval must be positive for the selected writeControl mode.",
                "Set a positive finite interval or review the dynamic expression manually.",
                SOURCE_DOCS, verification_level="static",
            ))
    return findings


def _region_checks(files: dict[str, ParsedDictionary]) -> list[Diagnostic]:
    relative = "constant/regionProperties"
    parsed = files.get(relative)
    application = _first(files.get("system/controlDict"), "application")
    cht = application in {"chtMultiRegionFoam", "chtMultiRegionSimpleFoam"}
    if parsed is None:
        if cht:
            return [Diagnostic(
                "OF-CROSS-005", "warning", "contextual", relative, 1, 1,
                f"CHT solver {application} has no constant/regionProperties dictionary.",
                "Add regionProperties with the fluid and solid region groups, or confirm the case is "
                "intentionally single-region before running the CHT solver.",
                SOURCE_DOCS, verification_level="contextual",
            )]
        return []
    entries = parsed.find("regions", scope=())
    line = entries[0].line if len(entries) == 1 else 1
    column = entries[0].column if len(entries) == 1 else 1
    try:
        metadata = parse_region_properties(parsed)
    except ValueError as exc:
        return [Diagnostic(
            "OF-CROSS-002", "warning", "contextual", relative, line, column,
            f"Region declarations could not be checked statically: {exc}.",
            "Use one static regions list with unique region names, then verify the listed regions manually.", SOURCE_DOCS, verification_level="contextual",
        )]

    groups = "; ".join(
        f"{group.region_type} ({', '.join(group.names)})" for group in metadata.groups
    )
    findings = [Diagnostic(
        "OF-CROSS-001", "info", "contextual", relative, line, column,
        f"Static multi-region declaration found: {groups}.",
        "Confirm the declared region names and their material and field dictionaries.", SOURCE_DOCS, verification_level="contextual",
    )]
    if cht:
        region_types = {group.region_type for group in metadata.groups}
        missing_groups = sorted({"fluid", "solid"} - region_types)
        if missing_groups:
            missing_text = " or ".join(missing_groups)
            findings.append(Diagnostic(
                "OF-CROSS-005", "warning", "contextual", relative, line, column,
                f"CHT solver {application} does not declare a {missing_text} region group.",
                "Declare both fluid and solid region groups in regionProperties, or confirm the case is "
                "intentionally single-region before running the CHT solver.",
                SOURCE_DOCS, verification_level="contextual",
            ))
    declared = set(metadata.names)
    initial_paths = [
        PurePosixPath(name) for name in files
        if PurePosixPath(name).parts and PurePosixPath(name).parts[0] in {"0", "0.orig"}
    ]
    missing_regions = [
        region for region in metadata.names
        if not any(len(path.parts) >= 3 and path.parts[1] == region for path in initial_paths)
    ]
    shared_initial = any(len(path.parts) == 2 for path in initial_paths)
    if missing_regions and shared_initial:
        findings.append(Diagnostic(
            "OF-CROSS-004", "info", "contextual", relative, line, column,
            "Shared root-level initial fields are present; region-specific field folders are not yet materialized.",
            "Check the case preparation workflow for a step that maps or creates initial fields for every declared region.", SOURCE_DOCS, verification_level="contextual",
        ))
    else:
        for region in missing_regions:
            findings.append(Diagnostic(
                "OF-CROSS-003", "warning", "contextual", relative, line, column,
                f"No bounded initial-field dictionary was found under 0/{region}/ or 0.orig/{region}/.",
                "Check whether the region has the required initial fields; static scanning skips mesh and result data.", SOURCE_DOCS, verification_level="contextual",
            ))
    undeclared = sorted({
        path.parts[1] for path in initial_paths
        if len(path.parts) >= 3 and path.parts[1] not in declared
    })
    for region in undeclared:
        findings.append(Diagnostic(
            "OF-CROSS-003", "warning", "contextual", relative, line, column,
            f"Initial-field directory {region!r} is not listed in regionProperties.",
            "Check regionProperties and the initial-field directory names for a spelling mismatch.", SOURCE_DOCS, verification_level="contextual",
        ))
    return findings


def _boundary_type_checks(files: dict[str, ParsedDictionary]) -> list[Diagnostic]:
    findings = []
    for relative, parsed in files.items():
        parts = PurePosixPath(relative).parts
        if not parts or parts[0] not in {"0", "0.orig"}:
            continue
        patches = [
            entry for entry in parsed.entries
            if entry.is_dictionary and entry.scope == ("boundaryField",)
        ]
        for patch in patches:
            scope = ("boundaryField", patch.key)
            types = parsed.find("type", scope=scope)
            if len(types) == 1 and (
                types[0].dynamic
                or (
                    len(types[0].value_tokens) == 1
                    and types[0].value_tokens[0].kind == "atom"
                )
            ):
                continue
            findings.append(Diagnostic(
                "OF-BC-002", "warning", "contextual", relative, patch.line, patch.column,
                f"Boundary patch {patch.key!r} has no single static type entry.",
                "Set one boundary-condition type for this patch or review its included/dynamic source manually.",
                SOURCE_DOCS, verification_level="contextual",
            ))
    return findings


def lint_case_layout(files: dict[str, ParsedDictionary], *, root_label: str = "case") -> tuple[Diagnostic, ...]:
    findings: list[Diagnostic] = []
    control = files.get("system/controlDict")
    if control is None:
        findings.append(Diagnostic(
            "OF-CASE-001", "warning", "contextual", root_label, 1, 1,
            "No system/controlDict was found in the scanned case paths.",
            "Confirm that the selected directory is an OpenFOAM case root.", SOURCE_DOCS, verification_level="contextual",
        ))
    application = _first(control, "application")
    if control is not None and not application:
        findings.append(Diagnostic(
            "OF-SOLVER-001", "warning", "contextual", "system/controlDict", 1, 1,
            "controlDict has no static application entry; solver identity cannot be checked.",
            "Set application to the solver selected for this case; dynamic values remain unresolved.", SOURCE_DOCS, verification_level="contextual",
        ))
    findings.extend(_control_time_checks(control))
    if application:
        for required in ("system/fvSchemes", "system/fvSolution"):
            if required not in files:
                findings.append(Diagnostic(
                    "OF-SOLVER-002", "warning", "contextual", required, 1, 1,
                    f"The selected solver {application!r} has no scanned {PurePosixPath(required).name} dictionary.",
                    "Confirm the selected solver's requirements; this advisory is not a universal required-file rule.", SOURCE_DOCS, verification_level="contextual",
                ))
    for relative, parsed in files.items():
        if relative.startswith(("0/", "0.orig/")) and not parsed.find("boundaryField"):
            findings.append(Diagnostic(
                "OF-BC-001", "warning", "contextual", relative, 1, 1,
                "Field dictionary has no boundaryField block.",
                "Check whether the file is a field dictionary and whether its patches are defined.", SOURCE_DOCS, verification_level="contextual",
            ))
    findings.extend(_boundary_type_checks(files))
    decompose = files.get("system/decomposeParDict")
    if decompose is not None:
        raw_count = _first(decompose, "numberOfSubdomains")
        try:
            count = int(raw_count or "")
        except ValueError:
            count = 0
        if count <= 0:
            findings.append(Diagnostic(
                "OF-PAR-001", "warning", "contextual", "system/decomposeParDict", 1, 1,
                "numberOfSubdomains is missing or is not a positive static integer.",
                "Choose a positive decomposition count; verify it against the allocated MPI ranks.", SOURCE_DOCS, verification_level="contextual",
            ))
        findings.extend(_parallel_layout_check(decompose))
    findings.extend(_region_checks(files))
    findings.extend(lint_solver_fields(files, application))
    return tuple(findings)

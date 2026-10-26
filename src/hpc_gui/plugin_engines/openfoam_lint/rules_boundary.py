"""Conservative field-boundary requirement checks for v2312 cases."""
from __future__ import annotations

from pathlib import PurePosixPath
from typing import Mapping

from hpc_gui.openfoam_core import Diagnostic, ParsedDictionary

FIXED_VALUE_SOURCE = (
    "https://doc.openfoam.com/2312/tools/processing/boundary-conditions/"
    "rtm/derived/general/fixedValue/"
)

RULES = {
    "OF-BC-003": {
        "title": "Fixed-value field entry",
        "severity": "warning",
        "confidence": "contextual",
        "verification_level": "contextual",
        "source": FIXED_VALUE_SOURCE,
    }
}


def lint_boundary_requirements(
    files: Mapping[str, ParsedDictionary],
) -> tuple[Diagnostic, ...]:
    """Warn only for a literal fixedValue patch without its required value."""
    findings: list[Diagnostic] = []
    for path, parsed in files.items():
        parts = PurePosixPath(path).parts
        if not parts or parts[0] not in {"0", "0.orig"}:
            continue
        if any(token.kind == "directive" for token in parsed.tokens):
            continue
        boundary_blocks = parsed.find("boundaryField", scope=())
        if len(boundary_blocks) != 1 or not boundary_blocks[0].is_dictionary:
            continue
        patches = [
            entry for entry in parsed.entries
            if entry.is_dictionary and entry.scope == ("boundaryField",)
        ]
        names = [entry.key for entry in patches]
        if len(names) != len(set(names)) or any(
            any(marker in name for marker in ".*+?[]()|{}^$\\")
            for name in names
        ):
            continue
        for patch in patches:
            scope = ("boundaryField", patch.key)
            types = parsed.find("type", scope=scope)
            if (
                len(types) != 1
                or types[0].dynamic
                or len(types[0].value_tokens) != 1
                or types[0].value_tokens[0].kind != "atom"
                or types[0].value_tokens[0].value != "fixedValue"
                or parsed.find("value", scope=scope)
            ):
                continue
            findings.append(Diagnostic(
                "OF-BC-003",
                "warning",
                "contextual",
                path,
                patch.line,
                patch.column,
                f"Boundary patch {patch.key!r} uses fixedValue but has no value entry.",
                "Add a value entry using the field's OpenFOAM value type.",
                FIXED_VALUE_SOURCE,
                verification_level="contextual",
            ))
    return tuple(findings)

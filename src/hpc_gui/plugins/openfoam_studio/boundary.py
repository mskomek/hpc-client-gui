"""Boundary/initial field matrix (W65 BC-007, G18/G19)."""

from __future__ import annotations

import math
import re

from hpc_gui.openfoam_core.boundary import (
    BC_TYPES,
    FIELD_DIMS,
    PATCH_TYPES,  # noqa: F401 — compatibility re-export
    allowed_bc,
)


_SCALAR = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?\Z")
_PATCH_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_.-]*\Z")


def _is_scalar(value: str) -> bool:
    return bool(_SCALAR.fullmatch(value)) and math.isfinite(float(value))


def _valid_internal_value(field: str, value: str) -> bool:
    if field != "U":
        return _is_scalar(value)
    if not value.startswith("(") or not value.endswith(")"):
        return False
    components = value[1:-1].split()
    return len(components) == 3 and all(_is_scalar(item) for item in components)


def render_field_file(field: str, internal: str, patches: dict[str, tuple[str, str]]) -> str:
    if field not in FIELD_DIMS:
        raise ValueError(f"field '{field}' has no dimension entry (RAW-ADVANCED only)")
    if not isinstance(internal, str) or not _valid_internal_value(field, internal):
        raise ValueError(f"field '{field}' internal value must be a numeric scalar/vector")
    if not isinstance(patches, dict):
        raise ValueError("patches must be a mapping of patch names to boundary conditions")
    lines = ["FoamFile", "{", "    version 2.0;", "    format ascii;",
             "    class volScalarField;" if field not in ("U",) else "    class volVectorField;",
             f"    object {field};", "}", f"dimensions {FIELD_DIMS[field]};",
             f"internalField uniform {internal};", "boundaryField", "{"]
    for patch, (kind, bc) in patches.items():
        if not isinstance(patch, str) or not _PATCH_NAME.fullmatch(patch):
            raise ValueError(f"invalid patch name '{patch}'")
        if bc not in BC_TYPES:
            raise ValueError(f"BC type '{bc}' unsupported in v2312 typed set")
        if bc not in allowed_bc(kind):
            raise ValueError(f"illegal BC '{bc}' for {kind} patch '{patch}'")
        lines += ["    " + patch, "    {", f"        type {bc};", "    }"]
    lines.append("}")
    return "\n".join(lines) + "\n"


def coverage_gaps(required_fields: list[str], present: dict[str, set[str]],
                  patches: list[str]) -> list[str]:
    gaps = []
    for field in required_fields:
        have = present.get(field, set())
        for patch in patches:
            if patch not in have and not patch.startswith("("):
                gaps.append(f"{field}:{patch}")
    return gaps

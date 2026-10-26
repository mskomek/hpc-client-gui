"""Boundary/initial field matrix (W65 BC-007, G18/G19)."""

from __future__ import annotations

from hpc_gui.openfoam_core.boundary import BC_TYPES, FIELD_DIMS, PATCH_TYPES, allowed_bc


def render_field_file(field: str, internal: str, patches: dict[str, tuple[str, str]]) -> str:
    if field not in FIELD_DIMS:
        raise ValueError(f"field '{field}' has no dimension entry (RAW-ADVANCED only)")
    lines = ["FoamFile", "{", "    version 2.0;", "    format ascii;",
             "    class volScalarField;" if field not in ("U",) else "    class volVectorField;",
             f"    object {field};", "}", f"dimensions {FIELD_DIMS[field]};",
             f"internalField uniform {internal};", "boundaryField", "{"]
    for patch, (kind, bc) in patches.items():
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

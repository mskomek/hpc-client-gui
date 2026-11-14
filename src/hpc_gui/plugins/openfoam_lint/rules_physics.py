"""Legacy prototypes for boundary/physics lint bindings (W65 LINT-013, G37).

Library-only: no production module imports this file. OF-SOLVER-010 is owned
by the canonical engine with warning/contextual semantics; the error/definite
variant here is not shipped.
"""

from __future__ import annotations

from hpc_gui.plugins.openfoam_lint.api import Diagnostic
from hpc_gui.openfoam_core import FIELD_DIMS, allowed_bc, required_fields_for


def lint_boundary_matrix(fields_present: dict[str, set[str]], patches: dict[str, str],
                         required_fields: list[str]) -> list[Diagnostic]:
    diags: list[Diagnostic] = []
    for field in required_fields:
        if field not in fields_present:
            diags.append(Diagnostic("OF-BC-010", "error", "definite", f"0/{field}",
                                    1, 1, f"missing required field '{field}'"))
            continue
        for patch in patches:
            if patch not in fields_present[field] and not patch.startswith("("):
                diags.append(Diagnostic("OF-BC-010", "error", "definite", f"0/{field}",
                                        1, 1, f"field '{field}' missing patch '{patch}'"))
    for patch, kind in patches.items():
        try:
            allowed_bc(kind)
        except ValueError:
            diags.append(Diagnostic("OF-BC-010", "error", "definite", "constant/polyMesh/boundary",
                                    1, 1, f"unknown patch kind '{kind}' for '{patch}'"))
    for field in fields_present:
        if field not in FIELD_DIMS:
            diags.append(Diagnostic("OF-PHYS-010", "warning", "heuristic", f"0/{field}",
                                    1, 1, f"field '{field}' has no typed dimension entry"))
    return diags


def lint_solver_fields(solver_family: str, model: str,
                       fields_present: list[str]) -> list[Diagnostic]:
    diags: list[Diagnostic] = []
    for need in required_fields_for(solver_family, model):
        if need not in fields_present:
            diags.append(Diagnostic("OF-SOLVER-010", "error", "definite", "0/", 1, 1,
                                    f"solver family '{solver_family}' missing field '{need}'"))
    return diags

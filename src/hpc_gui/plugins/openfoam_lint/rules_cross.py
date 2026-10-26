"""Cross-file physics/numerics/workflow lint rules (W65 LINT-013, G36/G37)."""

from __future__ import annotations

from hpc_gui.plugins.openfoam_lint.api import Diagnostic


def lint_case_files(files: dict[str, str]) -> list[Diagnostic]:
    """Lint a mapping of relpath -> text. Pure static analysis."""
    diags: list[Diagnostic] = []
    has_control = any(p.endswith("system/controlDict") for p in files)
    has_fv_schemes = any(p.endswith("system/fvSchemes") for p in files)
    has_fv_solution = any(p.endswith("system/fvSolution") for p in files)
    if has_control and not has_fv_schemes:
        diags.append(Diagnostic("OF-CROSS-010", "error", "definite", "system/fvSchemes",
                                1, 1, "controlDict present but fvSchemes missing (stale consumer)"))
    if has_control and not has_fv_solution:
        diags.append(Diagnostic("OF-CROSS-010", "error", "definite", "system/fvSolution",
                                1, 1, "controlDict present but fvSolution missing (stale consumer)"))
    solver = None
    for path, text in files.items():
        if path.endswith("system/controlDict"):
            for line in text.splitlines():
                if line.strip().startswith("application"):
                    solver = line.split()[-1].rstrip(";")
    if solver == "simpleFoam":
        for path, text in files.items():
            if path.endswith("system/fvSchemes") and "steadyState" not in text:
                diags.append(Diagnostic("OF-NUM-010", "error", "definite", path, 1, 1,
                                        "simpleFoam requires steadyState ddtSchemes"))
    if solver in ("chtMultiRegionSimpleFoam", "chtMultiRegionFoam"):
        if not any(p.endswith("constant/regionProperties") for p in files):
            diags.append(Diagnostic("OF-PHYS-010", "error", "definite",
                                    "constant/regionProperties", 1, 1,
                                    "CHT solver without regionProperties (missing region coupling)"))
    # Workflow: solver step without mesh producer note.
    tools = [t for t in files.get("__workflow_tools__", "").split(",") if t] if "__workflow_tools__" in files else []
    if tools and any("Foam" in t for t in tools) and not any("Mesh" in t for t in tools):
        diags.append(Diagnostic("OF-WF-010", "error", "heuristic", "__workflow__", 1, 1,
                                "solver node without mesh producer in workflow"))
    return diags


def lint_workflow_dag(node_tools: list[str], edges: list[tuple[str, str]],
                      node_ids: list[str]) -> list[Diagnostic]:
    diags: list[Diagnostic] = []
    for a, b in edges:
        if a not in node_ids or b not in node_ids:
            diags.append(Diagnostic("OF-WF-010", "error", "definite", "__workflow__", 1, 1,
                                    f"edge {a}->{b} references missing node (stale consumer)"))
    if any("Foam" in t for t in node_tools) and not any("Mesh" in t for t in node_tools):
        diags.append(Diagnostic("OF-WF-010", "error", "heuristic", "__workflow__", 1, 1,
                                "solver node without mesh producer in workflow"))
    return diags

"""Legacy prototypes for cross-file lint rules (W65 LINT-013, G36/G37).

Library-only: no production module imports this file. The canonical engine
(hpc_gui.plugin_engines.openfoam_lint) owns OF-CROSS-001..005, OF-NUM-010,
OF-PHYS-010 equivalents and the workflow rules; keep new behaviour there.
"""

from __future__ import annotations

from hpc_gui.openfoam_core import parse_dictionary, parse_region_properties
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
            applications = parse_dictionary(text, path=path).find("application")
            if len(applications) == 1:
                solver = applications[0].value.strip()
    if solver == "simpleFoam":
        for path, text in files.items():
            if path.endswith("system/fvSchemes"):
                parsed = parse_dictionary(text, path=path)
                defaults = parsed.find("default", ("ddtSchemes",))
                if len(defaults) != 1 or defaults[0].value.strip() != "steadyState":
                    line = defaults[0].line if defaults else 1
                    column = defaults[0].column if defaults else 1
                    diags.append(Diagnostic("OF-NUM-010", "error", "definite", path,
                                            line, column,
                                            "simpleFoam requires ddtSchemes default steadyState"))
    if solver in ("chtMultiRegionSimpleFoam", "chtMultiRegionFoam"):
        region_paths = [p for p in files if p.endswith("constant/regionProperties")]
        if not region_paths:
            diags.append(Diagnostic("OF-PHYS-010", "error", "definite",
                                    "constant/regionProperties", 1, 1,
                                    "CHT solver without regionProperties (missing region coupling)"))
        else:
            path = region_paths[0]
            parsed = parse_dictionary(files[path], path=path)
            if any(entry.dynamic for entry in parsed.entries):
                diags.append(Diagnostic("OF-PHYS-010", "warning", "heuristic", path,
                                        1, 1, "dynamic regionProperties cannot be statically verified"))
            else:
                try:
                    regions = parse_region_properties(parsed)
                except ValueError as exc:
                    diags.append(Diagnostic("OF-PHYS-010", "error", "definite", path,
                                            1, 1, f"invalid CHT regionProperties: {exc}"))
                else:
                    region_types = {group.region_type for group in regions.groups}
                    missing = sorted({"fluid", "solid"} - region_types)
                    if missing:
                        diags.append(Diagnostic(
                            "OF-PHYS-010", "error", "definite", path, 1, 1,
                            f"CHT regionProperties missing region groups: {', '.join(missing)}",
                        ))
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

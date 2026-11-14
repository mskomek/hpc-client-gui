"""W65 G36-G38: linter static rules, cross-file bindings, independence."""
from __future__ import annotations

from hpc_gui.plugins.openfoam_lint import RULE_FAMILIES
from hpc_gui.plugins.openfoam_lint.api import lint_text, rule_catalog
from hpc_gui.plugins.openfoam_lint.rules_cross import lint_case_files, lint_workflow_dag
from hpc_gui.plugins.openfoam_lint.rules_physics import lint_boundary_matrix, lint_solver_fields


def test_rule_ids_unique_and_prefixed():
    catalog = rule_catalog()
    ids = [r["id"] for r in catalog]
    assert len(ids) == len(set(ids))
    assert all(any(r["id"].startswith(p) for p in RULE_FAMILIES + ("OF-WF-", "OF-PHYS-", "OF-NUM-"))
               for r in catalog)


def test_static_dict_rules():
    diags = lint_text("system/controlDict", "application simpleFoam\n")  # missing ';'
    assert any(d.rule == "OF-DICT-001" for d in diags)
    clean = lint_text("system/fvSchemes", "ddtSchemes\n{\n}\n")
    assert not [d for d in clean if d.severity == "error"]


def test_executable_directive_flagged_not_run():
    diags = lint_text("0/U", "#codeStream\n{\ncode 1;\n}\n")
    assert any(d.rule == "OF-SEC-001" for d in diags)


def test_cross_file_missing_partner():
    diags = lint_case_files({"system/controlDict": "application simpleFoam;\n"})
    assert any("fvSchemes" in d.message for d in diags)


def test_cht_and_scheme_bindings():
    diags = lint_case_files({"system/controlDict": "application chtMultiRegionSimpleFoam;\n"})
    assert any(d.rule == "OF-PHYS-010" for d in diags)
    diags = lint_case_files({"system/controlDict": "application simpleFoam;\n",
                             "system/fvSchemes": "ddtSchemes { default Euler; }\n"})
    assert any(d.rule == "OF-NUM-010" for d in diags)
    commented = lint_case_files({
        "system/controlDict": "application simpleFoam;\n",
        "system/fvSchemes": "// steadyState mentioned in comment\nddtSchemes { default Euler; }\n",
    })
    numeric = [d for d in commented if d.rule == "OF-NUM-010"]
    assert len(numeric) == 1 and numeric[0].line == 2
    valid = lint_case_files({
        "system/controlDict": "application simpleFoam;\n",
        "system/fvSchemes": "ddtSchemes\n{\n    default steadyState;\n}\n",
    })
    assert not [d for d in valid if d.rule == "OF-NUM-010"]


def test_cht_region_properties_checks_static_fluid_and_solid_groups():
    files = {
        "system/controlDict": "application chtMultiRegionSimpleFoam;\n",
        "constant/regionProperties": "regions (fluid (water air));\n",
    }
    missing_solid = [d for d in lint_case_files(files) if d.rule == "OF-PHYS-010"]
    assert len(missing_solid) == 1 and "solid" in missing_solid[0].message

    files["constant/regionProperties"] = (
        "regions (fluid (water air) solid (steel));\n"
    )
    assert not [d for d in lint_case_files(files) if d.rule == "OF-PHYS-010"]


def test_boundary_and_solver_bindings():
    diags = lint_boundary_matrix({"U": {"inlet"}}, {"inlet": "inlet", "outlet": "outlet"}, ["U", "p"])
    assert any(d.rule == "OF-BC-010" for d in diags)
    diags = lint_solver_fields("rans-steady", "kEpsilon", ["U", "p"])
    assert any(d.rule == "OF-SOLVER-010" for d in diags)


def test_workflow_edges_and_independence():
    diags = lint_workflow_dag(["simpleFoam"], [("a", "b")], ["a"])
    assert any(d.rule == "OF-WF-010" for d in diags)
    ok = lint_workflow_dag(["blockMesh", "simpleFoam"], [], ["m", "s"])
    assert ok == []

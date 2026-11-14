"""W65 LINT-013: solver/time-scheme consistency across controlDict and fvSchemes."""
from __future__ import annotations

import pytest

from hpc_gui.plugin_engines.openfoam_lint.api import lint_files, rule_catalog


def _lint(solver: str, ddt: str):
    files = {
        "system/controlDict": f"application {solver};\n",
        "system/fvSchemes": f"ddtSchemes {{ default {ddt}; }}\n",
    }
    return [d for d in lint_files(files, case_context=True).diagnostics if d.rule_id == "OF-NUM-010"]


def test_transient_solver_rejects_steady_ddt_scheme():
    reported = _lint("icoFoam", "steadyState")

    assert len(reported) == 1
    assert reported[0].severity == "error"
    assert reported[0].confidence == "definite"
    assert reported[0].path == "system/fvSchemes"
    assert reported[0].line == 1
    assert "transient solver" in reported[0].message


def test_pimple_family_rejects_steady_ddt_scheme():
    assert len(_lint("pimpleFoam", "steadyState")) == 1
    assert len(_lint("interFoam", "steadyState")) == 1


def test_transient_solver_accepts_transient_scheme():
    for scheme in ("Euler", "backward", "CrankNicolson 0.9"):
        assert _lint("icoFoam", scheme) == []


def test_steady_solver_rejects_transient_ddt_scheme():
    reported = _lint("simpleFoam", "Euler")

    assert len(reported) == 1
    assert "requires ddtSchemes default steadyState" in reported[0].message


def test_steady_solver_accepts_steady_ddt_scheme():
    assert _lint("simpleFoam", "steadyState") == []
    assert _lint("buoyantSimpleFoam", "steadyState") == []


def test_dynamic_ddt_entry_is_not_judged():
    files = {
        "system/controlDict": "application icoFoam;\n",
        "system/fvSchemes": "ddtSchemes { default $ddtScheme; }\n",
    }

    assert [d for d in lint_files(files, case_context=True).diagnostics
            if d.rule_id == "OF-NUM-010"] == []


def test_unlisted_solver_is_left_alone():
    assert _lint("myCustomFoam", "steadyState") == []


def test_duplicate_ddt_default_is_not_judged():
    files = {
        "system/controlDict": "application simpleFoam;\n",
        "system/fvSchemes": (
            "ddtSchemes { default Euler; }\n"
            "ddtSchemes { default steadyState; }\n"
        ),
    }

    assert [d for d in lint_files(files, case_context=True).diagnostics
            if d.rule_id == "OF-NUM-010"] == []


def test_anchor_points_at_the_real_ddt_entry():
    files = {
        "system/controlDict": "application icoFoam;\n",
        "system/fvSchemes": (
            "FoamFile { version 2.0; }\n"
            "ddtSchemes\n"
            "{\n"
            "    default steadyState;\n"
            "}\n"
        ),
    }

    reported = [d for d in lint_files(files, case_context=True).diagnostics
                if d.rule_id == "OF-NUM-010"]

    assert len(reported) == 1
    assert reported[0].line == 4
    assert reported[0].column > 1


def test_every_studio_solver_has_a_time_treatment():
    from hpc_gui.openfoam_core.physics import SOLVER_TIME_TREATMENT
    from hpc_gui.plugins.openfoam_studio.solver_effects import SOLVER_BINARIES

    assert set(SOLVER_BINARIES) <= set(SOLVER_TIME_TREATMENT)


def test_unclassified_solver_cannot_generate_a_scheme():
    from hpc_gui.plugins.openfoam_studio.numerics_text import ddt_scheme

    with pytest.raises(ValueError):
        ddt_scheme("myCustomFoam")


def test_studio_numerics_guard_matches_the_linter():
    from hpc_gui.plugins.openfoam_studio import numerics

    schemes = ("Gauss linear", "Gauss upwind", "Gauss linear corrected")
    numerics.validate_fv_schemes(
        "Euler", *schemes, "laminar", tool="icoFoam",
    )
    numerics.validate_fv_schemes(
        "steadyState", *schemes, "rans-steady", tool="simpleFoam",
    )
    with pytest.raises(ValueError):
        numerics.validate_fv_schemes("steadyState", *schemes, "laminar", tool="icoFoam")
    with pytest.raises(ValueError):
        numerics.validate_fv_schemes("steadyState", *schemes, "multiphase", tool="interFoam")
    numerics.validate_fv_schemes("Euler", *schemes, "compressible", tool="rhoPimpleFoam")
    with pytest.raises(ValueError):
        numerics.validate_fv_schemes("steadyState", *schemes, "compressible", tool="rhoPimpleFoam")


def test_cht_region_schemes_are_checked():
    files = {
        "system/controlDict": "application chtMultiRegionFoam;\n",
        "system/fluid/fvSchemes": "ddtSchemes { default steadyState; }\n",
        "system/solid/fvSchemes": "ddtSchemes { default Euler; }\n",
    }

    reported = [d for d in lint_files(files, case_context=True).diagnostics
                if d.rule_id == "OF-NUM-010"]

    assert [d.path for d in reported] == ["system/fluid/fvSchemes"]
    assert "(region fluid)" in reported[0].message


def test_steady_cht_regions_accept_steady_state():
    files = {
        "system/controlDict": "application chtMultiRegionSimpleFoam;\n",
        "system/fluid/fvSchemes": "ddtSchemes { default steadyState; }\n",
        "system/solid/fvSchemes": "ddtSchemes { default steadyState; }\n",
    }

    assert [d for d in lint_files(files, case_context=True).diagnostics
            if d.rule_id == "OF-NUM-010"] == []


def test_region_schemes_are_checked_even_with_a_root_file():
    files = {
        "system/controlDict": "application chtMultiRegionFoam;\n",
        "system/fvSchemes": "ddtSchemes { default Euler; }\n",
        "system/fluid/fvSchemes": "ddtSchemes { default steadyState; }\n",
    }

    reported = [d for d in lint_files(files, case_context=True).diagnostics
                if d.rule_id == "OF-NUM-010"]

    assert [d.path for d in reported] == ["system/fluid/fvSchemes"]


@pytest.mark.parametrize("tool", ["icoFoam", "pimpleFoam", "simpleFoam"])
def test_studio_generated_case_passes_its_own_linter(tool):
    from hpc_gui.plugins.openfoam_studio.workflow import Node, WorkflowDAG
    from hpc_gui.plugins.openfoam_studio.workflow_compiler import compile_patch_plan

    params = {"endTime": 1.0, "writeInterval": 1.0}
    if tool != "simpleFoam":
        params["deltaT"] = 0.005
    dag = WorkflowDAG(
        nodes=[
            Node("m", "blockMesh", {"nx": 2, "ny": 2, "nz": 2, "patches": ["walls"]}),
            Node("s", tool, params),
        ],
        edges=[("m", "s")],
    )
    plan = compile_patch_plan(dag)
    files = {op.relpath: op.new_bytes for op in plan.ops if op.new_bytes}

    result = lint_files(files, case_context=True)

    assert [d for d in result.diagnostics if d.rule_id == "OF-NUM-010"] == []


def test_rule_catalog_documents_the_numerics_rule():
    metadata = rule_catalog()["OF-NUM-010"]
    assert metadata["title"] == "Solver time-scheme mismatch"
    assert metadata["severity"] == "error"
    assert metadata["confidence"] == "definite"
    assert metadata["verification_level"] == "static"

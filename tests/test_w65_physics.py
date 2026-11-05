"""W65 G14-G23: physics/materials/BC/numerics/solver-compat."""
from __future__ import annotations

import pytest

from hpc_gui.plugins.openfoam_studio import numerics as num
from hpc_gui.plugins.openfoam_studio import solver as solv
from hpc_gui.plugins.openfoam_studio.boundary import allowed_bc, coverage_gaps, render_field_file
from hpc_gui.plugins.openfoam_studio.cht import cht_interface_hint, validate_cht_regions
from hpc_gui.plugins.openfoam_studio.physics import (
    TURBULENCE_MODELS, material_entry, required_fields_for,
    transport_properties_dict, turbulence_properties_dict,
)


def test_materials_positive_only():
    entry = material_entry("air", 1.225, 1.789e-05)
    assert entry["provenance"] == "user-supplied" and entry["nu"] > 0
    with pytest.raises(ValueError):
        material_entry("bad", -1.0, 1.0)
    text = transport_properties_dict(998.0, 1.002e-03)
    assert "nu [0 2 -1 0 0 0 0]" in text


def test_turbulence_registry():
    assert set(TURBULENCE_MODELS["kOmegaSST"]["required_fields"]) == {"k", "omega"}
    assert "laminar" in turbulence_properties_dict("laminar")
    with pytest.raises(ValueError):
        turbulence_properties_dict("madeUpModel")
    assert "k" in required_fields_for("rans-steady", "kEpsilon")


def test_cht_validation():
    validate_cht_regions(["fluid"], ["solid"], ["fluid", "solid"])
    with pytest.raises(ValueError):
        validate_cht_regions([], ["solid"], ["solid"])
    with pytest.raises(ValueError):
        validate_cht_regions(["fluid"], [], ["other"])
    assert cht_interface_hint("fluid", "solid")["interface_type"] == "mappedWall"


def test_boundary_matrix():
    text = render_field_file("U", "(1 0 0)", {"inlet": ("inlet", "fixedValue")})
    assert "dimensions [0 1 -1 0 0 0 0]" in text
    with pytest.raises(ValueError):
        render_field_file("U", "(1 0 0)", {"inlet": ("inlet", "noSlip")})
    with pytest.raises(ValueError):
        render_field_file("nope", "0", {})
    gaps = coverage_gaps(["U", "p"], {"U": {"inlet"}}, ["inlet", "outlet"])
    assert "U:outlet" in gaps and "p:inlet" in gaps
    assert "noSlip" in allowed_bc("wall")


def test_numerics_time_and_schemes():
    text = num.render_control_dict("simpleFoam", 0, 100, 1, 10)
    assert "application simpleFoam" in text
    with pytest.raises(ValueError):
        num.render_control_dict("simpleFoam", 0, 100, 0, 10)
    num.validate_fv_schemes("steadyState", "Gauss linear", "Gauss upwind",
                            "Gauss linear corrected", "rans-steady")
    with pytest.raises(ValueError):
        num.validate_fv_schemes("Euler", "Gauss linear", "Gauss upwind",
                                "Gauss linear corrected", "rans-steady")
    with pytest.raises(ValueError):
        num.validate_fv_solution("noSolver", None, None)
    with pytest.raises(ValueError):
        num.validate_fv_solution("PCG", {"nCorrectors": 0}, None)


def test_solver_compat_and_run_plan():
    solv.check_solver_compat("simpleFoam", "kEpsilon", ["U", "p", "k", "epsilon"])
    with pytest.raises(ValueError):
        solv.check_solver_compat("simpleFoam", "kEpsilon", ["U", "p"])
    with pytest.raises(ValueError):
        solv.check_solver_compat("simpleFoam", "nope", ["U", "p"])
    plan = solv.render_run_plan("simpleFoam", parallel=False)
    assert "simpleFoam" in plan["allrun"] and plan["family"] == "rans-steady"
    with pytest.raises(ValueError):
        solv.render_run_plan("simpleFoam", parallel=True, n_subdomains=1, decompose=True)

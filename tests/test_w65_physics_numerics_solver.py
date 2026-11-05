"""Focused UNIT C regression tests for W65 physics, BC, numerics, solver."""
from __future__ import annotations
import pytest
from hpc_gui.openfoam_v2312 import bc, numerics, physics, solver
def _phys(**overrides):
    base = {"solver": "simpleFoam", "flow_model": "RAS-kOmegaSST"}
    base.update(overrides)
    return physics.PhysicsSpec(**base)
def _bc(**overrides):
    base = {"patch": "inlet", "patch_kind": "patch", "field": "U", "bc_type": "fixedValue", "dimensions": "[0 1 -1 0 0 0 0]"}
    base.update(overrides)
    return bc.BCSpec(**base)
def _control(**overrides):
    base = {"application": "simpleFoam", "start_from": "firstTime", "start_time": 0.0, "end_time": 100.0, "delta_t": 0.005, "write_control": "timeStep", "write_interval": 10.0}
    base.update(overrides)
    return numerics.ControlSpec(**base)
def _run(**overrides):
    base = {"stages": ("preflight", "mesh", "check", "solve", "post"), "solver": "simpleFoam"}
    base.update(overrides)
    return solver.RunSpec(**base)
@pytest.mark.unit
def test_valid_steady_ras_passes():
    assert physics.validate_physics(_phys()) == ()
@pytest.mark.unit
def test_valid_transient_laminar_passes():
    spec = _phys(solver="icoFoam", flow_model="laminar", transient=True)
    assert physics.validate_physics(spec) == ()
@pytest.mark.unit
def test_valid_cht_two_regions_passes():
    spec = _phys(solver="chtMultiRegionSimpleFoam", flow_model="laminar", heat_transfer=True, cht=True, regions=("fluid", "solid"))
    assert physics.validate_physics(spec) == ()
@pytest.mark.unit
def test_unknown_solver_and_model_rejected():
    errors = physics.validate_physics(_phys(solver="myFoam", flow_model="magic"))
    assert any("solver" in e for e in errors)
    assert any("flow model" in e for e in errors)
@pytest.mark.unit
def test_transient_steady_solver_rejected():
    assert any("transient" in e for e in physics.validate_physics(_phys(transient=True)))
@pytest.mark.unit
def test_compressible_incompatible_solver_rejected():
    assert any("compressible" in e for e in physics.validate_physics(_phys(compressible=True)))
@pytest.mark.unit
def test_cht_wrong_solver_rejected():
    spec = _phys(cht=True, regions=("fluid", "solid"))
    assert any("CHT" in e for e in physics.validate_physics(spec))
@pytest.mark.unit
def test_cht_single_region_rejected():
    spec = _phys(solver="chtMultiRegionSimpleFoam", cht=True, regions=("fluid",))
    assert any("two regions" in e for e in physics.validate_physics(spec))
@pytest.mark.unit
def test_heat_transfer_without_cht_or_compressible_rejected():
    assert any("heat transfer" in e for e in physics.validate_physics(_phys(heat_transfer=True)))
@pytest.mark.unit
def test_duplicate_and_empty_regions_rejected():
    assert any("duplicate" in e for e in physics.validate_physics(_phys(regions=("a", "a"))))
    assert any("empty" in e for e in physics.validate_physics(_phys(regions=("fluid", " "))))
@pytest.mark.unit
def test_physics_round_trip():
    spec = _phys(solver="chtMultiRegionSimpleFoam", cht=True, regions=("fluid", "solid"))
    assert physics.PhysicsSpec.from_dict(spec.to_dict()) == spec
@pytest.mark.unit
def test_valid_bc_passes():
    assert bc.validate_bc(_bc()) == ()
@pytest.mark.unit
def test_noslip_wall_passes():
    assert bc.validate_bc(_bc(patch="walls", patch_kind="wall", bc_type="noSlip")) == ()
@pytest.mark.unit
def test_noslip_on_pressure_rejected():
    spec = _bc(field="p", bc_type="noSlip", dimensions="[0 2 -2 0 0 0 0]")
    assert any("not valid for field" in e for e in bc.validate_bc(spec))
@pytest.mark.unit
def test_wrong_dimensions_rejected():
    assert any("dimensions" in e for e in bc.validate_bc(_bc(dimensions="[0 0 0 1 0 0 0]")))
@pytest.mark.unit
def test_unknown_patch_field_bc_rejected():
    errors = bc.validate_bc(_bc(patch_kind="portal", field="Q", bc_type="magic"))
    assert any("patch kind" in e for e in errors)
    assert any("field" in e for e in errors)
@pytest.mark.unit
def test_bc_round_trip():
    assert bc.BCSpec.from_dict(_bc().to_dict()) == _bc()
@pytest.mark.unit
def test_valid_control_passes():
    assert numerics.validate_control(_control()) == ()
@pytest.mark.unit
def test_unknown_application_rejected():
    assert any("application" in e for e in numerics.validate_control(_control(application="myFoam")))
@pytest.mark.unit
def test_bad_time_window_rejected():
    assert any("endTime" in e for e in numerics.validate_control(_control(end_time=0.0)))
    assert any("deltaT" in e for e in numerics.validate_control(_control(delta_t=0.0)))
    assert any("writeInterval" in e for e in numerics.validate_control(_control(write_interval=-1.0)))
@pytest.mark.unit
def test_unknown_write_control_rejected():
    assert any("writeControl" in e for e in numerics.validate_control(_control(write_control="sometimes")))
@pytest.mark.unit
def test_bad_solver_entry_rejected():
    bad = numerics.SolverEntry(field=" ", linear_solver="CG", tolerance=2.0, rel_tol=1.0)
    errors = numerics.validate_solver_entry(bad)
    assert any("field" in e for e in errors)
    assert any("linear solver" in e for e in errors)
    assert any("tolerance" in e for e in errors)
    assert any("relTol" in e for e in errors)
@pytest.mark.unit
def test_valid_solver_entry_passes():
    entry = numerics.SolverEntry(field="p", linear_solver="GAMG", tolerance=1e-06, rel_tol=0.01)
    assert numerics.validate_solver_entry(entry) == ()
@pytest.mark.unit
def test_decompose_validation():
    assert numerics.validate_decompose(4, "scotch") == ()
    errors = numerics.validate_decompose(0, "magic")
    assert any("subdomains" in e for e in errors)
    assert any("method" in e for e in errors)
@pytest.mark.unit
def test_control_round_trip():
    assert numerics.ControlSpec.from_dict(_control().to_dict()) == _control()
@pytest.mark.unit
def test_valid_serial_pipeline_passes():
    assert solver.validate_run(_run()) == ()
@pytest.mark.unit
def test_valid_parallel_pipeline_passes():
    spec = _run(stages=("preflight", "mesh", "check", "decompose", "solve", "reconstruct", "post"), parallel=True, subdomains=4)
    assert solver.validate_run(spec) == ()
@pytest.mark.unit
def test_solve_before_mesh_rejected():
    spec = _run(stages=("solve", "mesh", "check"))
    assert any("precedes mesh" in e for e in solver.validate_run(spec))
@pytest.mark.unit
def test_decompose_without_parallel_rejected():
    spec = _run(stages=("mesh", "check", "decompose", "solve"))
    assert any("parallel" in e for e in solver.validate_run(spec))
@pytest.mark.unit
def test_reconstruct_without_decompose_rejected():
    spec = _run(stages=("mesh", "check", "solve", "reconstruct", "post"))
    assert any("decompose" in e for e in solver.validate_run(spec))
@pytest.mark.unit
def test_post_without_solve_rejected():
    spec = _run(stages=("mesh", "check", "post"))
    assert any("solve" in e for e in solver.validate_run(spec))
@pytest.mark.unit
def test_unknown_stage_rejected():
    assert any("unknown" in e for e in solver.validate_run(_run(stages=("mesh", "warp"))))
@pytest.mark.unit
def test_run_round_trip():
    assert solver.RunSpec.from_dict(_run().to_dict()) == _run()
@pytest.mark.unit
def test_matrix_still_validates():
    from hpc_gui.openfoam_v2312.ability_matrix import build_matrix, validate_matrix
    rows = build_matrix()
    validate_matrix(rows)
    assert len(rows) == 22
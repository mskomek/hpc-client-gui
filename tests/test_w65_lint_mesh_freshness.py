"""W65 LINT-013: surface geometry newer than the generated mesh is reported."""
from __future__ import annotations

import os

from hpc_gui.plugin_engines.openfoam_lint.api import lint_paths, rule_catalog


def _case(tmp_path, surface_time: float, mesh_time: float):
    case = tmp_path / "case"
    (case / "system").mkdir(parents=True)
    (case / "system" / "controlDict").write_text("application snappyHexMesh\n", encoding="utf-8")
    surface_dir = case / "constant" / "triSurface"
    surface_dir.mkdir(parents=True)
    surface = surface_dir / "body.stl"
    surface.write_text("solid body\n", encoding="utf-8")
    mesh_dir = case / "constant" / "polyMesh"
    mesh_dir.mkdir(parents=True)
    points = mesh_dir / "points"
    points.write_text("0\n", encoding="utf-8")
    os.utime(surface, (surface_time, surface_time))
    os.utime(points, (mesh_time, mesh_time))
    return case


def test_newer_surface_is_reported(tmp_path):
    case = _case(tmp_path, surface_time=2_000_000_000, mesh_time=1_900_000_000)

    reported = [d for d in lint_paths([str(case)]).diagnostics if d.rule_id == "OF-CROSS-006"]

    assert len(reported) == 1
    assert reported[0].path == "constant/triSurface/body.stl"
    assert "newer than" in reported[0].message


def test_older_surface_is_clean(tmp_path):
    case = _case(tmp_path, surface_time=1_900_000_000, mesh_time=2_000_000_000)

    assert [d for d in lint_paths([str(case)]).diagnostics if d.rule_id == "OF-CROSS-006"] == []


def test_missing_mesh_points_is_not_judged(tmp_path):
    case = tmp_path / "no-mesh"
    (case / "system").mkdir(parents=True)
    (case / "system" / "controlDict").write_text("application snappyHexMesh\n", encoding="utf-8")
    (case / "constant" / "triSurface").mkdir(parents=True)
    (case / "constant" / "triSurface" / "body.stl").write_text("solid body\n", encoding="utf-8")

    assert [d for d in lint_paths([str(case)]).diagnostics if d.rule_id == "OF-CROSS-006"] == []


def test_rule_catalog_documents_the_freshness_rule():
    metadata = rule_catalog()["OF-CROSS-006"]
    assert metadata["title"] == "Surface newer than mesh"
    assert metadata["severity"] == "info"


def test_equal_timestamps_are_clean(tmp_path):
    case = _case(tmp_path, surface_time=2_000_000_000, mesh_time=2_000_000_000)

    assert [d for d in lint_paths([str(case)]).diagnostics if d.rule_id == "OF-CROSS-006"] == []


def test_non_surface_suffix_is_ignored(tmp_path):
    case = _case(tmp_path, surface_time=1_900_000_000, mesh_time=2_000_000_000)
    notes = case / "constant" / "triSurface" / "notes.txt"
    notes.write_text("x", encoding="utf-8")
    os.utime(notes, (2_100_000_000, 2_100_000_000))

    assert [d for d in lint_paths([str(case)]).diagnostics if d.rule_id == "OF-CROSS-006"] == []


def test_directory_named_like_a_surface_is_ignored(tmp_path):
    case = _case(tmp_path, surface_time=1_900_000_000, mesh_time=2_000_000_000)
    (case / "constant" / "triSurface" / "fake.stl").mkdir()

    assert [d for d in lint_paths([str(case)]).diagnostics if d.rule_id == "OF-CROSS-006"] == []


def test_points_directory_is_not_judged(tmp_path):
    case = tmp_path / "case"
    (case / "system").mkdir(parents=True)
    (case / "system" / "controlDict").write_text("application snappyHexMesh\n", encoding="utf-8")
    (case / "constant" / "triSurface").mkdir(parents=True)
    (case / "constant" / "triSurface" / "body.stl").write_text("solid b\n", encoding="utf-8")
    (case / "constant" / "polyMesh" / "points").mkdir(parents=True)

    assert [d for d in lint_paths([str(case)]).diagnostics if d.rule_id == "OF-CROSS-006"] == []


def test_many_surfaces_are_capped_with_a_notice(tmp_path):
    case = _case(tmp_path, surface_time=1_900_000_000, mesh_time=2_000_000_000)
    surface_dir = case / "constant" / "triSurface"
    for index in range(70):
        extra = surface_dir / f"part{index:03d}.stl"
        extra.write_text("solid p\n", encoding="utf-8")
        os.utime(extra, (2_100_000_000, 2_100_000_000))

    reported = [d for d in lint_paths([str(case)]).diagnostics if d.rule_id == "OF-CROSS-006"]

    assert len(reported) == 9
    assert any("covered only the first batch" in d.message for d in reported)



def _reacting_case(tmp_path, surface_time: float, mesh_time: float):
    """A reacting-family case whose surface postdates the mesh.

    This is the W65 LINT-013 fixture the matrix still listed as missing: a
    reactingFoam case with its chemistry dictionaries and species fields, plus
    a triSurface newer than constant/polyMesh/points. It checks that the
    freshness rule fires in the reacting family without disturbing the
    reacting field checks (OF-SOLVER-010 must stay silent here).
    """
    case = tmp_path / "reacting"
    (case / "system").mkdir(parents=True)
    (case / "system" / "controlDict").write_text("application reactingFoam\n", encoding="utf-8")
    (case / "system" / "fvSchemes").write_text("ddtSchemes { default Euler; }\n", encoding="utf-8")
    (case / "system" / "fvSolution").write_text("solvers { }\n", encoding="utf-8")
    (case / "constant").mkdir(parents=True)
    (case / "constant" / "thermophysicalProperties").write_text(
        "thermoType { type hePsiThermo; mixture reactingMixture; }\n", encoding="utf-8"
    )
    (case / "constant" / "reactions").write_text(
        "species ( CH4 O2 N2 );\nreactions { }\n", encoding="utf-8"
    )
    (case / "constant" / "turbulenceProperties").write_text(
        "simulationType laminar;\n", encoding="utf-8"
    )
    zero = case / "0"
    zero.mkdir()
    for field in ("U", "p", "T", "CH4", "O2", "N2"):
        (zero / field).write_text("dimensions [0 0 0 0 0 0 0];\n", encoding="utf-8")
    surface_dir = case / "constant" / "triSurface"
    surface_dir.mkdir()
    surface = surface_dir / "body.stl"
    surface.write_text("solid body\n", encoding="utf-8")
    mesh_dir = case / "constant" / "polyMesh"
    mesh_dir.mkdir()
    points = mesh_dir / "points"
    points.write_text("0\n", encoding="utf-8")
    os.utime(surface, (surface_time, surface_time))
    os.utime(points, (mesh_time, mesh_time))
    return case


def test_reacting_case_with_newer_surface_reports_only_the_freshness_rule(tmp_path):
    case = _reacting_case(tmp_path, surface_time=2_000_000_000, mesh_time=1_900_000_000)

    diagnostics = lint_paths([str(case)]).diagnostics

    freshness = [d for d in diagnostics if d.rule_id == "OF-CROSS-006"]
    solver_fields = [d for d in diagnostics if d.rule_id == "OF-SOLVER-010"]
    assert len(freshness) == 1
    assert freshness[0].path == "constant/triSurface/body.stl"
    assert solver_fields == []


def test_reacting_case_with_older_surface_is_clean(tmp_path):
    case = _reacting_case(tmp_path, surface_time=1_900_000_000, mesh_time=2_000_000_000)

    diagnostics = lint_paths([str(case)]).diagnostics

    assert [d for d in diagnostics if d.rule_id == "OF-CROSS-006"] == []
    assert [d for d in diagnostics if d.rule_id == "OF-SOLVER-010"] == []

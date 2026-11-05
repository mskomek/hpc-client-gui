"""W65 G06-G13: geometry/mesh pipeline incl. negatives."""
from __future__ import annotations

import pytest

from hpc_gui.plugins.openfoam_studio import blockmesh as bm
from hpc_gui.plugins.openfoam_studio import mesh_regions as mr
from hpc_gui.plugins.openfoam_studio import snappy as sn
from hpc_gui.plugins.openfoam_studio.cad_gate import CadBlockedExternal, require_converter, step_intake_status
from hpc_gui.plugins.openfoam_studio.geometry_import import inspect_surface
from hpc_gui.plugins.openfoam_studio.mesh_quality import parse_check_mesh, quality_verdict


def test_ascii_stl_head_bounds():
    head = b"solid box\nfacet normal 0 0 1\nouter loop\nvertex 0 0 0\nvertex 1 0 0\nvertex 0 1 0\nendloop\nendfacet\nendsolid\n"
    info = inspect_surface("box.stl", len(head) * 10, head)
    assert info.fmt == "STL" and info.bounds is not None and info.facet_count == 1


def test_invalid_utf8_geometry_sample_is_reported_without_data_loss():
    head = b"solid box\xff\nfacet normal 0 0 1\n"
    info = inspect_surface("box.stl", len(head) * 10, head)
    assert info.facet_count == 1
    assert "geometry preview sample contains invalid UTF-8; metadata may be incomplete" in info.warnings


def test_geometry_negatives():
    with pytest.raises(ValueError):
        inspect_surface("part.step", 100, b"data")
    with pytest.raises(ValueError):
        inspect_surface("empty.stl", 0, b"")


def test_cad_gate_blocked_external(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda *a, **k: None)
    with pytest.raises(CadBlockedExternal):
        require_converter()
    status = step_intake_status("part.step")
    assert status["status"] == "BLOCKED_EXTERNAL"


def test_blockmesh_golden_and_bad():
    text = bm.render_block_mesh_dict(10, 10, 10, ["inlet", "outlet"])
    assert "hex (0 1 2 3 4 5 6 7) (10 10 10)" in text and "inlet" in text
    with pytest.raises(ValueError):
        bm.validate_topology(0, 1, 1)
    with pytest.raises(ValueError):
        bm.render_block_mesh_dict(10, 10, 10, [])


def test_snappy_negative_and_threshold():
    text = sn.render_snappy_dict(max_global_cells=1000, refinement_surfaces=["wall"])
    assert "maxGlobalCells 1000" in text
    with pytest.raises(ValueError):
        sn.render_snappy_dict(max_global_cells=10**9)


def test_checkmesh_parse_and_unknown():
    q = parse_check_mesh("Mesh stats:\n    cells:  1000\n    points: 2000\nMesh OK.\n")
    assert (q.cells, q.points) == (1000, 2000)
    assert quality_verdict(q) == "PASS-parsed"
    empty = parse_check_mesh("garbage with no numbers\n")
    assert quality_verdict(empty) == "UNKNOWN-no-data"


def test_converters_and_regions():
    assert mr.converter_for("grid.msh") in ("gmshToFoam", "fluentMeshToFoam")
    with pytest.raises(ValueError):
        mr.converter_for("grid.step")
    with pytest.raises(ValueError):
        mr.converter_argv("foamToVTK", "grid.msh")
    text = mr.region_properties_dict(["fluid"], ["solid"])
    assert "fluid" in text and "solid" in text
    with pytest.raises(ValueError):
        mr.region_properties_dict([], ["solid"])

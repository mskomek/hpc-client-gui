"""W65r2 F7: typed subsets (G07/G12/G16/G17/G19)."""
from __future__ import annotations

import pytest

from hpc_gui.plugins.openfoam_studio import (
    advanced_boundaries,
    advanced_physics,
    cht,
    mesh_regions,
    surface_actions,
)

PATCHES = {"inlet": ("inlet", "fixedValue"), "outlet": ("outlet", "zeroGradient"),
           "walls": ("wall", "noSlip")}


def test_surface_quality_wizard():
    ok = surface_actions.surface_quality_report(facet_count=120, bounds=(1, 1, 1),
                                                size_bytes=512, warnings=["open edge"])
    assert ok["quality"] == "UNKNOWN" or ok["facets"] == 120
    assert ok["warnings"] == ["open edge"]
    with pytest.raises(ValueError):
        surface_actions.surface_quality_report(facet_count=1, bounds=None, size_bytes=0)
    with pytest.raises(ValueError):
        surface_actions.surface_quality_report(facet_count=1, bounds=None,
                                               size_bytes=300 * 1024 * 1024)
    text = surface_actions.feature_extract_dict(["wing.stl"], included_angle=120.0)
    assert "wing.stl" in text and "surfaceFeatureExtractDict" in text
    with pytest.raises(ValueError):
        surface_actions.feature_extract_dict([])
    with pytest.raises(ValueError):
        surface_actions.feature_extract_dict(["a.stl"], included_angle=0.0)
    with pytest.raises(ValueError):
        surface_actions.feature_extract_dict(["a;rm.stl"])


def test_zone_split_ops():
    text = mesh_regions.topo_set_dict([{"name": "rotZone", "type": "cellZoneSet",
                                        "source": "boxToCell"}])
    assert "rotZone" in text and "cellZoneSet" in text
    with pytest.raises(ValueError):
        mesh_regions.topo_set_dict([])
    with pytest.raises(ValueError):
        mesh_regions.topo_set_dict([{"name": "x", "type": "nope"}])
    assert "-overwrite" in mesh_regions.zone_argv("splitMeshRegions")
    assert "-overwrite" in mesh_regions.zone_argv("createPatch")
    assert mesh_regions.zone_argv("topoSet") == ["topoSet", "-case", "."]
    with pytest.raises(ValueError):
        mesh_regions.zone_argv("teleportMesh")
    assert "restore" in mesh_regions.zone_rollback_note("topoSet")


def test_cht_full_dicts():
    thermo = cht.region_thermophysical_dict("fluid", fluid=True)
    assert "thermophysicalProperties" in thermo and "fluid" in thermo
    solid = cht.region_thermophysical_dict("solid", fluid=False)
    assert "heSolidThermo" in solid
    with pytest.raises(ValueError):
        cht.region_thermophysical_dict("fluid", fluid=True, rho=-1.0)
    with pytest.raises(ValueError):
        cht.region_thermophysical_dict("a b", fluid=True)
    field = cht.cht_region_temperature_field("fluid", 300.0, [("hotWall", "hotWallSolid")])
    assert "hotWallSolid" in field
    with pytest.raises(ValueError):
        cht.cht_region_temperature_field("fluid", 300.0, [("x", "x")])


def test_advanced_physics_subsets():
    assert advanced_physics.advanced_availability("multiphase") == "ACTIVE-TYPED"
    assert advanced_physics.advanced_availability("reacting") == "UNSUPPORTED"
    assert advanced_physics.advanced_availability("whatever") == "RAW-ADVANCED"
    alpha = advanced_physics.alpha_water_field(0.5, PATCHES)
    assert "alpha.water" in alpha
    with pytest.raises(ValueError):
        advanced_physics.alpha_water_field(1.5, PATCHES)
    with pytest.raises(ValueError):
        advanced_physics.thermophysical_properties_dict("reacting")
    with pytest.raises(ValueError):
        advanced_physics.thermophysical_properties_dict("compressible", rho=0.0)
    g = advanced_physics.gravity_dict()
    assert "value (0 -9.81 0)" in g
    with pytest.raises(ValueError):
        advanced_physics.gravity_dict((0.0, 1.0))


def test_coupled_mapped_cyclic_profiles():
    entries = advanced_boundaries.coupled_temperature_entries("hotWall", "hotWallSolid")
    assert "Tnbr" in entries["hotWall"]
    with pytest.raises(ValueError):
        advanced_boundaries.coupled_temperature_entries("same", "same")
    with pytest.raises(ValueError):
        advanced_boundaries.coupled_temperature_entries("a", "b", kappa=0.0)
    cyclic = advanced_boundaries.cyclic_entries("left", "right")
    assert "neighbourPatch right" in cyclic["left"]
    with pytest.raises(ValueError):
        advanced_boundaries.cyclic_entries("solo", "solo")
    mapped = advanced_boundaries.mapped_wall_entry("patch1", "patch2", (0.0, 0.0, 0.1))
    assert "mappedWall" in mapped
    with pytest.raises(ValueError):
        advanced_boundaries.mapped_wall_entry("p", "q", (0.0, 0.0))

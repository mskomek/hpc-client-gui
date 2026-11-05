"""W65 G03-G05: catalog inventory, typed schemas, availability gating."""
from __future__ import annotations

import pytest

from hpc_gui.plugins.openfoam_studio import catalog_inventory as inv
from hpc_gui.plugins.openfoam_studio.availability import gate_or_disable, probe
from hpc_gui.plugins.openfoam_studio.command_schemas import SCHEMAS, SchemaError, validate


def test_legacy_8_preserved():
    rows = {r["command_name"]: r for r in inv.inventory()}
    for name in ("blockMesh", "checkMesh", "decomposePar", "splitMeshRegions",
                 "icoFoam", "chtMultiRegionSimpleFoam", "reconstructPar", "postProcess"):
        assert name in rows and rows[name]["legacy_021"] is True


def test_coverage_counts_honest():
    counts = inv.coverage_counts()
    assert counts["classified"] == counts["discovered_in_scope"]
    assert counts["legacy_021_preserved"] == 8
    assert "BLOCKED_ENV" in counts["note"]


def test_schema_accepts_and_rejects():
    out = validate("blockMesh", {"nx": 10, "ny": 10, "nz": 10, "patches": ["inlet"]})
    assert out["nx"] == 10
    with pytest.raises(SchemaError):
        validate("blockMesh", {"nx": 10, "ny": 10, "nz": 10, "patches": ["x"], "bogus": 1})
    with pytest.raises(SchemaError):
        validate("blockMesh", {"nx": 0, "ny": 1, "nz": 1, "patches": ["x"]})
    with pytest.raises(SchemaError):
        validate("noSuchTool", {})


def test_every_typed_schema_has_source():
    for tool, spec in SCHEMAS.items():
        assert spec.get("source"), tool
        assert spec["params"], tool


def test_availability_never_executes():
    res = gate_or_disable("definitely-not-a-binary-xyz", "ACTIVE-TYPED")
    assert res["status"] == "UNAVAILABLE" and res["enabled"] is False
    uns = probe("anything", "UNSUPPORTED")
    assert uns.status == "UNSUPPORTED" and uns.found is False


def test_every_row_has_source_provenance():
    for row in inv.inventory():
        assert row["source_path"], row["command_name"]
        assert row["source_revision"] == "OpenFOAM-v2312", row["command_name"]
        assert row["reason"], row["command_name"]
        assert row["proof_level"] in (
            "V2312-SOURCE", "OFFICIAL-DOC", "V2312-HELP",
            "RUNTIME-EXECUTED", "STRUCTURAL", "UNVERIFIED",
        ), row["command_name"]


def test_no_duplicate_or_unknown_names():
    first = inv.inventory()
    second = inv.inventory()
    assert first == second
    names = [r["command_name"] for r in first]
    assert len(set(names)) == len(names)
    uids = [r["uid"] for r in first]
    assert len(set(uids)) == len(uids)


def test_coverage_denominator_complete():
    counts = inv.coverage_counts()
    assert counts["denominator"] == {
        "solver_exe": 122, "utility_exe": 175, "non_exe_configs": 8,
    }
    assert counts["discovered_in_scope"] == 305
    assert counts["classified"] == 305
    assert sum(counts["by_availability"].values()) == 305
    assert counts["active_typed"] == 20 == len(SCHEMAS)
    assert counts["by_availability"] == {
        "ACTIVE-TYPED": 20, "RAW-ADVANCED": 284, "UNSUPPORTED": 1,
    }


def test_status_invariants():
    rows = {r["command_name"]: r for r in inv.inventory()}
    for name, row in rows.items():
        if row["availability"] == "ACTIVE-TYPED":
            assert name in SCHEMAS, name
        else:
            assert name not in SCHEMAS, name
    for name in ("blockMesh", "checkMesh", "decomposePar", "splitMeshRegions",
                 "icoFoam", "chtMultiRegionSimpleFoam", "reconstructPar", "postProcess"):
        assert rows[name]["availability"] == "ACTIVE-TYPED", name


def test_sample_is_not_standalone_binary():
    rows = {r["command_name"]: r for r in inv.inventory()}
    sample = rows["sample"]
    assert sample["kind"] == "function-object-config"
    assert sample["proof_level"] == "V2312-SOURCE"
    assert sample["availability"] == "RAW-ADVANCED"
    assert "sampleDict" in sample["source_path"]


def test_source_taxonomy_spot_paths():
    rows = {r["command_name"]: r for r in inv.inventory()}
    assert rows["simpleFoam"]["source_path"] == "applications/solvers/incompressible/simpleFoam"
    assert rows["chtMultiRegionSimpleFoam"]["source_path"] == (
        "applications/solvers/heatTransfer/chtMultiRegionFoam/chtMultiRegionSimpleFoam")
    assert rows["blockMesh"]["source_path"] == "applications/utilities/mesh/generation/blockMesh"
    assert rows["explicitRhoFoam"]["source_path"].startswith("modules/OpenQBMM/")
    assert rows["gridToSTL"]["source_path"].startswith("modules/avalanche/")
    assert rows["yPlus"]["source_path"] == "src/functionObjects/field/yPlus"
    assert rows["probes"]["source_path"] == "src/sampling/probes"
    assert rows["gmshToFoam"]["kind"] == "converter"
    assert rows["overSimpleFoam"]["category"] == "solver"
    assert rows["overSimpleFoam"]["solver_family"] == "incompressible"


def test_archive_provenance_constants():
    assert inv.ARCHIVE_NAME == "OpenFOAM-v2312.tgz"
    assert len(inv.ARCHIVE_SHA256) == 64
    int(inv.ARCHIVE_SHA256, 16)
    assert inv.ARCHIVE_BYTES == 69027976
    assert inv.SOURCE_TAG == "OpenFOAM-v2312"
    assert inv.SOLVER_EXE_COUNT == 122
    assert inv.UTILITY_EXE_COUNT == 175

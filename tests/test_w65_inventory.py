"""Focused UNIT A regression tests for the W65 v2312 inventory (W65)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hpc_gui.openfoam_v2312 import ability_matrix
from hpc_gui.openfoam_v2312 import inventory

P0_NAMES = (
    "blockMesh",
    "checkMesh",
    "chtMultiRegionSimpleFoam",
    "decomposePar",
    "icoFoam",
    "postProcess",
    "reconstructPar",
    "simpleFoam",
    "splitMeshRegions",
)

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "w65" / "v2312_inventory.json"


@pytest.mark.unit
def test_version_pin_matches_wave_spec() -> None:
    assert inventory.V2312_VERSION == "v2312"
    assert inventory.V2312_TAG == "OpenFOAM-v2312"
    assert inventory.V2312_COMMIT == "1d8f0d55f79e6488dae75e4b839e358a88af77b5"


@pytest.mark.unit
def test_p0_inventory_is_complete() -> None:
    assert inventory.list_commands() == P0_NAMES


@pytest.mark.unit
def test_no_live_execution_is_claimed() -> None:
    for entry in inventory.COMMANDS:
        assert entry.execution == inventory.EXECUTION_DRAFT_ONLY


@pytest.mark.unit
def test_tiers_are_valid_and_honestly_raw() -> None:
    for entry in inventory.COMMANDS:
        assert entry.tier in inventory.VALID_TIERS
        assert entry.tier == inventory.TIER_RAW
        assert entry.reason != ""


@pytest.mark.unit
def test_export_is_deterministic() -> None:
    assert inventory.to_dicts() == inventory.to_dicts()
    assert [row["name"] for row in inventory.to_dicts()] == list(P0_NAMES)


@pytest.mark.unit
def test_roundtrip_preserves_entries() -> None:
    assert inventory.from_dicts(inventory.to_dicts()) == inventory.COMMANDS


@pytest.mark.unit
def test_checked_in_fixture_matches_export() -> None:
    assert json.loads(FIXTURE.read_text(encoding="utf-8")) == inventory.to_dicts()


@pytest.mark.unit
def test_unknown_command_is_rejected() -> None:
    with pytest.raises(KeyError):
        inventory.get_command("noSuchUtility")


@pytest.mark.unit
def test_invalid_tier_is_rejected() -> None:
    bad = dict(inventory.COMMANDS[0].to_dict())
    bad["tier"] = "certified"
    with pytest.raises(ValueError):
        inventory.CommandEntry.from_dict(bad)


@pytest.mark.unit
def test_ability_matrix_covers_all_requirements() -> None:
    rows = ability_matrix.build_matrix()
    assert len(rows) == 22
    ability_matrix.validate_matrix(rows)
    by_id = {row.feature_id: row for row in rows}
    assert by_id["HPC-W65-VM-017"].status == ability_matrix.STATUS_BLOCKED
    assert by_id["HPC-W65-RUNTIME-018"].status == ability_matrix.STATUS_BLOCKED
    assert by_id["HPC-W65-CLOSE-022"].status == ability_matrix.STATUS_BLOCKED
    assert all(row.status != ability_matrix.STATUS_DONE for row in rows)
    assert ability_matrix.to_dicts() == ability_matrix.to_dicts()

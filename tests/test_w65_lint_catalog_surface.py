"""W65 LINT-013: every rule added for this wave stays in the public catalog."""
from __future__ import annotations

from hpc_gui.plugin_engines.openfoam_lint.api import rule_catalog
from hpc_gui.plugins.openfoam_lint.api import rule_catalog as legacy_catalog


EXPECTED = {
    "OF-SEC-005": "Untrusted shell script",
    "OF-NUM-010": "Solver time-scheme mismatch",
    "OF-MESH-010": "Incomplete snappy dictionary",
    "OF-CROSS-005": "CHT region groups",
    "OF-CROSS-006": "Surface newer than mesh",
    "OF-SOLVER-010": "Solver initial fields",
}


def test_engine_catalog_exposes_every_new_rule():
    catalog = rule_catalog()
    for rule_id, title in EXPECTED.items():
        assert catalog[rule_id]["title"] == title


def test_legacy_facade_projects_every_new_rule():
    ids = {entry["id"] for entry in legacy_catalog()}
    assert set(EXPECTED) <= ids


def test_new_rules_carry_identity_metadata():
    catalog = rule_catalog()
    for rule_id in EXPECTED:
        metadata = catalog[rule_id]
        assert metadata["severity"] in {"info", "warning", "error"}
        assert metadata["confidence"] in {"certain", "definite", "structural", "contextual", "heuristic"}

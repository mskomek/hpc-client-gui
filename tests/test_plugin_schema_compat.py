"""Cluster-profile schema capability contract tests.

These lock the historical release facts (PLUGIN-1), the current capability
set (PLUGIN-2), and the compatibility-floor gate that prevents the published
TRUBA 1.4.0 / v1.5.8 regression from recurring (PLUGIN-3/4/5/7/8).
"""

from __future__ import annotations

import pytest

from hpc_gui import __version__
from hpc_gui.plugins.compatibility import (
    is_app_compatible,
    minimum_admitted_version,
    parse_version,
)
from hpc_gui.plugins.registry_client import find_registry_entry
from hpc_gui.plugins.schema_compat import (
    MIN_APP_VERSION_FOR_SCHEMA,
    PLUGIN_INFRASTRUCTURE_VERSION,
    SUPPORTED_CLUSTER_PROFILE_SCHEMAS,
    app_supports_schema,
    minimum_app_version_for_schema,
    schema_floor_error,
    supported_schemas_label,
    unsupported_schema_message,
)
from hpc_gui.plugins.validator import validate_cluster_profile_dict

RELEASED_1_5_8 = "1.5.8"
FIRST_SCHEMA3_RELEASE = "1.5.9"


# ---------------------------------------------------------------------------
# PLUGIN-1 / PLUGIN-2: capability generations
# ---------------------------------------------------------------------------


@pytest.mark.contract
def test_plugin_1_released_1_5_8_supports_schemas_1_and_2():
    """Historical release facts are not rewritten by newer code."""
    assert MIN_APP_VERSION_FOR_SCHEMA[1] == "1.4.0"
    assert MIN_APP_VERSION_FOR_SCHEMA[2] == "1.5.5"
    released = parse_version(RELEASED_1_5_8)
    supported_then = [
        schema
        for schema in SUPPORTED_CLUSTER_PROFILE_SCHEMAS
        if parse_version(minimum_app_version_for_schema(schema)) <= released
    ]
    assert supported_then == [1, 2]
    assert parse_version(MIN_APP_VERSION_FOR_SCHEMA[3]) > released


@pytest.mark.contract
def test_plugin_2_current_release_supports_schema_3_and_4():
    assert MIN_APP_VERSION_FOR_SCHEMA[3] == FIRST_SCHEMA3_RELEASE
    assert MIN_APP_VERSION_FOR_SCHEMA[4] == FIRST_SCHEMA3_RELEASE
    assert SUPPORTED_CLUSTER_PROFILE_SCHEMAS == (1, 2, 3, 4)
    assert is_app_compatible(">=" + FIRST_SCHEMA3_RELEASE, __version__)


# ---------------------------------------------------------------------------
# PLUGIN-3 / PLUGIN-4: TRUBA 1.4.0 compatibility decisions
# ---------------------------------------------------------------------------


@pytest.mark.contract
def test_plugin_3_truba_1_4_0_is_incompatible_with_released_1_5_8():
    assert is_app_compatible(">=1.5.9", RELEASED_1_5_8) is False


@pytest.mark.contract
def test_plugin_4_truba_1_4_0_requires_first_schema3_release():
    for requires_app in (">=1.5.9", ">=1.5.9,<2.0.0"):
        assert is_app_compatible(requires_app, FIRST_SCHEMA3_RELEASE) is True
        assert is_app_compatible(requires_app, RELEASED_1_5_8) is False


# ---------------------------------------------------------------------------
# PLUGIN-5: latest-compatible fallback resolution
# ---------------------------------------------------------------------------


def _synthetic_registry() -> dict:
    def entry(version: str, requires_app: str) -> dict:
        return {
            "id": "org.hpcclient.truba",
            "name": "TRUBA",
            "version": version,
            "plugin_api": 1,
            "type": "cluster-profile",
            "description": "d",
            "publisher": "HPC Client GUI",
            "requires_app": requires_app,
            "manifest_path": f"plugins/truba/{version}/manifest.json",
            "manifest_sha256": "0" * 64,
            "official": True,
        }

    return {
        "schema_version": 1,
        "plugin_api": 1,
        "repository": {"raw_base": "https://example.invalid/"},
        "plugins": [
            entry("1.0.0", ">=1.4.0"),
            entry("1.3.0", ">=1.5.5"),
            entry("1.4.0", ">=1.5.9"),
            entry("1.5.0", ">=1.5.9"),
        ],
    }


@pytest.mark.contract
def test_plugin_5_latest_compatible_fallback_per_app_line():
    registry = _synthetic_registry()
    assert find_registry_entry(
        registry, "org.hpcclient.truba", app_version=RELEASED_1_5_8
    )["version"] == "1.3.0"
    assert find_registry_entry(
        registry, "org.hpcclient.truba", app_version=FIRST_SCHEMA3_RELEASE
    )["version"] == "1.5.0"
    assert find_registry_entry(
        registry, "org.hpcclient.truba", app_version="1.5.4"
    )["version"] == "1.0.0"


# ---------------------------------------------------------------------------
# PLUGIN-7: schema floor rule
# ---------------------------------------------------------------------------


@pytest.mark.contract
def test_app_version_supports_schema_question_is_answerable():
    assert app_supports_schema("1.5.8", 3) is False
    assert app_supports_schema("1.5.8", 2) is True
    assert app_supports_schema("1.5.9", 3) is True
    assert app_supports_schema("1.5.9", 4) is True
    assert app_supports_schema("1.5.5", 2) is True
    assert app_supports_schema("1.5.4", 2) is False
    assert app_supports_schema("1.5.4", 1) is True
    assert app_supports_schema("1.5.9", 999) is False
    assert app_supports_schema("not-a-version", 1) is False


@pytest.mark.contract
def test_plugin_7_schema_floor_violations_are_detected():
    # The exact published regression: schema 3 claimed against >=1.5.8.
    assert schema_floor_error(3, ">=1.5.8") is not None
    # Honest floor.
    assert schema_floor_error(3, ">=1.5.9") is None
    # Schema 2 first shipped in 1.5.5.
    assert schema_floor_error(2, ">=1.5.4") is not None
    assert schema_floor_error(2, ">=1.5.5") is None
    # Schema 1 claims below the plugin infrastructure baseline are vacuous.
    assert schema_floor_error(1, ">=1.3.0") is None


@pytest.mark.contract
def test_plugin_7_floor_uses_the_lowest_admitted_version():
    assert minimum_admitted_version(">=1.4.0,<2.0.0") == (1, 4, 0)
    assert minimum_admitted_version(">1.5.8") == (1, 5, 9)
    assert minimum_admitted_version("<2.0.0") == (0, 0, 0)
    assert minimum_admitted_version("==1.5.*") == (1, 5, 0)
    assert minimum_admitted_version(">=oops") is None


# ---------------------------------------------------------------------------
# PLUGIN-8: unsupported future schemas stay fail-closed
# ---------------------------------------------------------------------------


@pytest.mark.contract
def test_plugin_8_future_schema_is_rejected():
    base = {"profile_id": "truba", "name": "TRUBA", "scheduler": "slurm"}
    problems = validate_cluster_profile_dict({"schema_version": 999, **base})
    assert any("schema_version must be one of" in problem for problem in problems)
    for version in SUPPORTED_CLUSTER_PROFILE_SCHEMAS:
        assert validate_cluster_profile_dict({"schema_version": version, **base}) == []


@pytest.mark.contract
def test_unsupported_schema_message_is_actionable():
    message = unsupported_schema_message(999, app_version="1.5.9")
    assert "schema 999" in message
    assert "1.5.9" in message
    assert supported_schemas_label() in message
    assert "Install a newer application release" in message


@pytest.mark.contract
def test_plugin_infrastructure_baseline_is_release_fact():
    assert PLUGIN_INFRASTRUCTURE_VERSION == "1.4.0"

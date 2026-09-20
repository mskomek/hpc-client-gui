"""W08 — provider schema, optional capability and isolation semantics.

Purpose IDs:
    DEF-W08-001 / REQ-W08-SCHEMA-002-006-009
        malformed storage/quota sections must fail closed at validation and
        must never crash host startup (v1/v4 skipped the shape checks that
        v2/v3 enforced; a v4 ``"storage": "nope"`` payload passed validation
        and raised ``ValueError`` out of ``load_installed_plugins``).
    CON-W08-001  validator shape contract across schema versions 1-4.
    REQ-W08-SCHEMA-001  five optional-capability absence states stay distinct.
    NEG-W08-008  configuration diagnostics name provider+field, never secrets.
    CON-W08-010  optional linter-engine dependency failure stays isolated
        (CONDITIONAL SCHEMA-010 live-path verification).
    CON-W08-004  optional-field defaults carry explicit semantics
        (CONDITIONAL SCHEMA-004 live-path verification).
    NEG-W08-003  unknown manifest keys are rejected intentionally.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from hpc_gui.plugins.loader import load_installed_plugins
from hpc_gui.plugins.models import PLUGIN_API_VERSION, build_cluster_profile
from hpc_gui.plugins.storage import write_active_versions
from hpc_gui.plugins.validator import validate_cluster_profile_dict, validate_manifest_dict
from hpc_gui.services.provider_capabilities import NOT_DECLARED, build_provider_capability_view
from hpc_gui.services.quota_monitor import QuotaResult, format_quota_result, quota_gate

APP_VERSION = "9.9.9"


def _manifest(plugin_id: str, **overrides) -> dict:
    base = {
        "schema_version": 1,
        "plugin_api": PLUGIN_API_VERSION,
        "id": plugin_id,
        "name": plugin_id,
        "version": "1.0.0",
        "publisher": "HPC Client GUI",
        "license": "MIT",
        "description": f"{plugin_id} cluster profile.",
        "requires_app": ">=1.0.0",
        "capabilities": ["cluster-profile"],
        "entrypoints": {"cluster_profiles": ["cluster-profile.json"]},
        "files": [],
    }
    base.update(overrides)
    return base


def _install(root: Path, manifest: dict, profile: dict, rel: str = "cluster-profile.json") -> None:
    pkg = root / "packages" / manifest["id"] / manifest["version"]
    pkg.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(profile).encode("utf-8")
    (pkg / rel).write_bytes(payload)
    stored = {
        **manifest,
        "files": [
            {
                "path": rel,
                "sha256": hashlib.sha256(payload).hexdigest(),
                "size": len(payload),
                "role": "cluster-profile",
            }
        ],
    }
    (pkg / "manifest.json").write_text(json.dumps(stored), encoding="utf-8")


def _activate(root: Path, *manifests: dict) -> None:
    write_active_versions({item["id"]: item["version"] for item in manifests}, root=root)


GOOD_PROFILE = {
    "schema_version": 1,
    "profile_id": "good",
    "name": "Good",
    "scheduler": "slurm",
}


# ---------------------------------------------------------------------------
# DEF-W08-001 — malformed sections fail closed, startup survives
# ---------------------------------------------------------------------------


@pytest.mark.contract
@pytest.mark.parametrize("schema_version", [1, 4])
@pytest.mark.parametrize("section", ["storage", "quota_sources"])
def test_malformed_section_shape_is_rejected_before_build(tmp_path: Path, schema_version: int, section: str):
    """REQ-W08-SCHEMA-002/006: v1/v4 enforce the same section shape as v2/v3."""
    profile = {
        "schema_version": schema_version,
        "profile_id": "evil",
        "name": "Evil",
        "scheduler": "slurm",
        section: "nope",
    }
    errors = validate_cluster_profile_dict(profile)
    assert errors == [f"cluster profile '{section}' must be a list"]


@pytest.mark.contract
@pytest.mark.parametrize("schema_version", [1, 4])
def test_section_item_without_id_is_rejected(tmp_path: Path, schema_version: int):
    """REQ-W08-SCHEMA-002: id-less storage/quota rows cannot slip through."""
    profile = {
        "schema_version": schema_version,
        "profile_id": "evil",
        "name": "Evil",
        "scheduler": "slurm",
        "storage": [{"label": "No id"}],
        "quota_sources": [{"enabled": True}],
    }
    errors = validate_cluster_profile_dict(profile)
    assert "cluster profile 'storage[0]' needs a non-empty id" in errors
    assert "cluster profile 'quota_sources[0]' needs a non-empty id" in errors


@pytest.mark.integration
@pytest.mark.parametrize("schema_version", [1, 4])
@pytest.mark.parametrize("section", ["storage", "quota_sources"])
def test_malformed_plugin_does_not_prevent_startup(tmp_path: Path, schema_version: int, section: str):
    """DEF-W08-001: one malformed plugin is diagnosed; the host still starts.

    Before the fix this raised ``ValueError`` out of the loader (reproduced
    at baseline ``0f8902a0``); the sibling plugin never loaded.
    """
    good = _manifest("org.hpcclient.good")
    evil = _manifest("org.hpcclient.evil")
    _install(tmp_path, good, GOOD_PROFILE)
    _install(
        tmp_path,
        evil,
        {
            "schema_version": schema_version,
            "profile_id": "evil",
            "name": "Evil",
            "scheduler": "slurm",
            section: "nope",
        },
    )
    _activate(tmp_path, good, evil)

    result = load_installed_plugins(root=tmp_path, app_version=APP_VERSION)

    assert [plugin.manifest.id for plugin in result.plugins] == ["org.hpcclient.good"]
    assert [problem.plugin_id for problem in result.problems] == ["org.hpcclient.evil"]
    assert f"cluster profile '{section}' must be a list" in result.problems[0].reason
    # Deterministic repeat: discovery ordering is stable for tests and UI.
    again = load_installed_plugins(root=tmp_path, app_version=APP_VERSION)
    assert [plugin.manifest.id for plugin in again.plugins] == ["org.hpcclient.good"]


# ---------------------------------------------------------------------------
# REQ-W08-SCHEMA-001 — five absence states stay distinct
# ---------------------------------------------------------------------------


@pytest.mark.contract
def test_optional_quota_absence_states_do_not_collapse():
    """SCHEMA-001: absent/unavailable/failed/empty-zero/invalid never merge."""
    not_declared = build_provider_capability_view({})
    assert not_declared.capabilities[3].id == "quota"
    assert not_declared.capabilities[3].declared == NOT_DECLARED
    assert quota_gate(None) == "not_configured"

    declared_disabled = quota_gate({"command_template": "quota {user}", "enabled": False})
    assert declared_disabled == "disabled"

    probe_failed = QuotaResult("error", error="timeout")
    assert probe_failed.state == "error" and probe_failed.used_bytes is None

    valid_zero = QuotaResult("ok", used_bytes=0, soft_limit_bytes=20)
    assert format_quota_result(valid_zero) == "0 / 20 bytes"

    invalid = quota_gate({"command_template": "quota {user}", "enabled": True, "scope": "bogus"})
    assert invalid == "invalid_configuration"

    markers = {
        "not_declared": (NOT_DECLARED, "not_configured"),
        "disabled": declared_disabled,
        "failed": (probe_failed.state, probe_failed.used_bytes),
        "valid_zero": format_quota_result(valid_zero),
        "invalid": invalid,
    }
    assert len({repr(value) for value in markers.values()}) == 5
    # None of them collapses to 0, empty string or generic success.
    for value in markers.values():
        assert value not in (0, "", "ok", "success", "eligible")


# ---------------------------------------------------------------------------
# NEG-W08-008 — diagnostics identify provider+field, never secrets
# ---------------------------------------------------------------------------


@pytest.mark.contract
def test_config_errors_never_echo_secret_values(tmp_path: Path):
    """SCHEMA-008: diagnostics name the field; secret payload stays out."""
    secret = "s3cr3t-pw-9f2c"
    profile = {
        "schema_version": 4,
        "profile_id": "evil",
        "name": "Evil",
        "scheduler": "slurm",
        "description": secret,
        "storage": "nope",
    }
    errors = validate_cluster_profile_dict(profile)
    assert errors
    assert secret not in " ".join(errors)

    manifest = _manifest("org.hpcclient.evil")
    # The offending key NAME is the field identifier diagnostics must name;
    # the secret VALUE must never appear.
    manifest["exec_hook"] = secret
    manifest_errors = validate_manifest_dict(manifest)
    assert manifest_errors
    assert any("unknown properties" in error for error in manifest_errors)
    assert secret not in " ".join(manifest_errors)

    evil = _manifest("org.hpcclient.evil")
    _install(tmp_path, evil, profile)
    _activate(tmp_path, evil)
    result = load_installed_plugins(root=tmp_path, app_version=APP_VERSION)
    assert result.plugins == []
    assert secret not in " ".join(problem.reason for problem in result.problems)


# ---------------------------------------------------------------------------
# CON-W08-010 / CON-W08-004 — conditional live-path verification
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_optional_linter_engine_failure_stays_isolated(tmp_path: Path):
    """SCHEMA-010: a bad optional engine rejects only its own plugin."""
    good = _manifest("org.hpcclient.good")
    bad_manifest = _manifest(
        "org.hpcclient.lint",
        capabilities=["cluster-profile", "linter-tool"],
        entrypoints={
            "cluster_profiles": ["cluster-profile.json"],
            "linter_engine": "engine/missing/__init__.py",
        },
    )
    _install(tmp_path, good, GOOD_PROFILE)
    _install(tmp_path, bad_manifest, GOOD_PROFILE)
    _activate(tmp_path, good, bad_manifest)

    result = load_installed_plugins(root=tmp_path, app_version=APP_VERSION)

    assert [plugin.manifest.id for plugin in result.plugins] == ["org.hpcclient.good"]
    assert [problem.plugin_id for problem in result.problems] == ["org.hpcclient.lint"]


@pytest.mark.contract
def test_minimal_v4_template_defaults_are_explicit():
    """SCHEMA-004: optional sections default to explicit empty, not garbage."""
    template = build_cluster_profile(
        {"schema_version": 4, "profile_id": "mini", "name": "Mini", "scheduler": "slurm"}
    ).to_provider_template()
    assert template["storage"] == []
    assert template["quota_sources"] == []
    assert template["job_details"] is None
    assert template["accounting"] is None
    assert template["cluster_status"] is None


# ---------------------------------------------------------------------------
# NEG-W08-003 — unknown keys rejected intentionally (SCHEMA-003)
# ---------------------------------------------------------------------------


@pytest.mark.contract
def test_unknown_manifest_keys_are_rejected_intentionally():
    """SCHEMA-003: unknown top-level manifest keys fail closed, loudly."""
    manifest = _manifest("org.hpcclient.evil")
    manifest["exec_hook"] = "rm -rf"
    errors = validate_manifest_dict(manifest)
    assert any("unknown properties" in error for error in errors)

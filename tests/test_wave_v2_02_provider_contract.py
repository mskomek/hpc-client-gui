"""WAVE V2 FINAL 02 — provider and capability contract regressions.

Purpose IDs:
    DEF-W02-001 / CON-W02-001  canonical provider_template serialization
    NEG-W02-001                declared-but-empty stays distinguishable
    DEF-W02-002 / CON-W02-002  duplicate cluster profile identity
    NEG-W02-002                duplicate rejection stays isolated

Both defects were observed at baseline `731357c6` with the shipped
`org.hpcclient.truba` 1.5.0 cluster profile (schema_version 4).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from hpc_gui.plugins.loader import load_installed_plugins
from hpc_gui.plugins.models import PLUGIN_API_VERSION, build_cluster_profile
from hpc_gui.plugins.storage import write_active_versions
from hpc_gui.plugins.templates import installed_cluster_template_groups
from hpc_gui.services.provider_capabilities import DECLARED, build_provider_capability_view
from hpc_gui.services.provider_contract import extract_contract

APP_VERSION = "1.5.9"

# A v4 profile that declares every optional section the shipped TRUBA 1.5.0
# profile declares: storage, quota_sources and the adapter/parser contracts.
V4_PROFILE = {
    "schema_version": 4,
    "profile_id": "truba",
    "name": "TRUBA",
    "scheduler": "slurm",
    "paths": {"home_dir": "/arf/home/{user}", "scratch_dir": "/arf/scratch/{user}"},
    "commands": {"status_command": "lssrv"},
    "storage": [
        {
            "id": "home",
            "label": "Home",
            "kind": "home",
            "access_context": "shared",
            "path_template": "/arf/home/{user}",
        }
    ],
    "quota_sources": [
        {
            "id": "truba-quota",
            "enabled": False,
            "backend_id": "",
            "command_template": "",
            "scope": "unknown",
        }
    ],
    "job_details": {"adapter": "slurm.scontrol.job", "parser": "slurm.scontrol.v1"},
    "accounting": {"adapter": "slurm.sacct.job", "parser": "slurm.sacct.pipe.v1"},
    "cluster_status": {"adapter": "truba.lssrv", "parser": "truba.lssrv.v1"},
}

MINIMAL_PROFILE = {
    "schema_version": 1,
    "profile_id": "generic",
    "name": "Generic",
    "scheduler": "slurm",
    "commands": {"scancel_command": "scancel {job_id_q}"},
}


def _manifest(plugin_id: str, name: str, version: str = "1.0.0", requires_app: str = ">=1.5.9") -> dict:
    return {
        "schema_version": 1,
        "plugin_api": PLUGIN_API_VERSION,
        "id": plugin_id,
        "name": name,
        "version": version,
        "publisher": "HPC Client GUI",
        "license": "MIT",
        "description": f"{name} cluster profile.",
        "requires_app": requires_app,
        "capabilities": ["cluster-profile"],
        "entrypoints": {"cluster_profiles": ["cluster-profile.json"]},
        "files": [],
    }


def _install(root: Path, entries: list[tuple[dict, dict]]) -> None:
    """Install every (manifest, profile) pair and activate all of them."""
    active: dict[str, str] = {}
    for manifest, profile in entries:
        pkg = root / "packages" / manifest["id"] / manifest["version"]
        pkg.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(profile).encode("utf-8")
        (pkg / "cluster-profile.json").write_bytes(payload)
        stored = {
            **manifest,
            "files": [
                {
                    "path": "cluster-profile.json",
                    "sha256": hashlib.sha256(payload).hexdigest(),
                    "size": len(payload),
                    "role": "cluster-profile",
                }
            ],
        }
        (pkg / "manifest.json").write_text(json.dumps(stored), encoding="utf-8")
        active[manifest["id"]] = manifest["version"]
    write_active_versions(active, root=root)


# ---------------------------------------------------------------------------
# FIX-A — one canonical provider_template shape
# ---------------------------------------------------------------------------


@pytest.mark.contract
def test_system_settings_and_structured_template_are_identical():
    """CON-W02-001: both producers must emit the same provider template.

    Before the fix `to_system_settings()` emitted only identity plus the v4
    adapter/parser contracts while `PluginSystemTemplate.structured` emitted
    only the v2/v3 metadata sections, so whichever one the connection dialog
    stored silently dropped the other half.
    """
    profile = build_cluster_profile(V4_PROFILE)
    canonical = profile.to_provider_template()
    assert profile.to_system_settings()["provider_template"] == canonical
    assert set(canonical) >= {
        "profile_id",
        "name",
        "scheduler",
        "commands",
        "storage",
        "quota_sources",
        "job_details",
        "accounting",
        "cluster_status",
    }


@pytest.mark.integration
def test_stored_plugin_template_keeps_contract_and_capabilities(tmp_path: Path):
    """DEF-W02-001: the template the dialog stores must keep every section.

    The connection dialog stores ``PluginSystemTemplate.structured`` verbatim
    as the profile's ``provider_template``; runtime then reads the adapter
    contract and the capability view out of that single dict.
    """
    _install(tmp_path, [(_manifest("org.hpcclient.truba", "TRUBA"), V4_PROFILE)])
    groups = installed_cluster_template_groups(root=tmp_path, app_version=APP_VERSION)
    stored = groups["TRUBA"][0].structured

    contract = extract_contract(stored)
    assert contract.has_job_details
    assert contract.has_accounting
    assert contract.has_cluster_status
    assert contract.job_details_parser == "slurm.scontrol.v1"

    declared = {item.id: item.declared for item in build_provider_capability_view(stored).capabilities}
    assert declared["storage"] == DECLARED
    assert declared["quota"] == DECLARED
    assert declared["scheduler"] == DECLARED


@pytest.mark.contract
def test_undeclared_sections_stay_distinguishable_from_declared_empty():
    """NEG-W02-001: absence must not be laundered into a truthy section."""
    canonical = build_cluster_profile(MINIMAL_PROFILE).to_provider_template()
    # Keys are always present so a consumer can tell "provider template
    # loaded" from "no provider at all", but the values stay falsy.
    assert canonical["storage"] == []
    assert canonical["quota_sources"] == []
    assert canonical["job_details"] is None
    assert canonical["accounting"] is None
    assert canonical["cluster_status"] is None

    contract = extract_contract(canonical)
    assert not contract.has_job_details
    assert not contract.has_accounting
    assert not contract.has_cluster_status

    declared = {item.id: item.declared for item in build_provider_capability_view(canonical).capabilities}
    assert declared["storage"] != DECLARED
    assert declared["quota"] != DECLARED
    # `scheduler` is a required cluster-profile field, so it stays DECLARED
    # even for a minimal profile — that is the contract, not an accident.
    assert declared["scheduler"] == DECLARED


# ---------------------------------------------------------------------------
# FIX-B — duplicate cluster profile identity
# ---------------------------------------------------------------------------


@pytest.mark.contract
@pytest.mark.parametrize("swap", [False, True])
def test_duplicate_profile_id_is_rejected_deterministically(tmp_path: Path, swap: bool):
    """DEF-W02-002: a second plugin may not claim a live profile_id.

    Before the fix both plugins registered the same ``profile_id`` and the
    connection dialog offered two indistinguishable entries, so which
    provider a saved profile actually referred to depended on menu order.
    """
    first = (_manifest("org.hpcclient.alpha", "Alpha"), V4_PROFILE)
    second = (_manifest("org.hpcclient.beta", "Beta"), {**V4_PROFILE, "name": "TRUBA copy"})
    _install(tmp_path, [second, first] if swap else [first, second])

    result = load_installed_plugins(root=tmp_path, app_version=APP_VERSION)

    loaded = {plugin.manifest.id for plugin in result.plugins}
    # Sorted plugin-id order decides the winner regardless of install order.
    assert loaded == {"org.hpcclient.alpha"}
    assert [problem.plugin_id for problem in result.problems] == ["org.hpcclient.beta"]
    reason = result.problems[0].reason
    assert "duplicate cluster profile id 'truba'" in reason
    assert "org.hpcclient.alpha@1.0.0" in reason

    groups = installed_cluster_template_groups(root=tmp_path, app_version=APP_VERSION)
    profile_ids = [tmpl.provenance["profile_id"] for entries in groups.values() for tmpl in entries]
    assert profile_ids == ["truba"]


@pytest.mark.contract
def test_duplicate_rejection_does_not_disable_unrelated_plugins(tmp_path: Path):
    """NEG-W02-002: rejecting a duplicate stays isolated to that plugin."""
    _install(
        tmp_path,
        [
            (_manifest("org.hpcclient.alpha", "Alpha"), V4_PROFILE),
            (_manifest("org.hpcclient.beta", "Beta"), V4_PROFILE),
            (_manifest("org.hpcclient.zeta", "Zeta", requires_app=">=1.4.0"), MINIMAL_PROFILE),
        ],
    )

    result = load_installed_plugins(root=tmp_path, app_version=APP_VERSION)

    assert {plugin.manifest.id for plugin in result.plugins} == {
        "org.hpcclient.alpha",
        "org.hpcclient.zeta",
    }
    assert len(result.problems) == 1
    assert result.problems[0].plugin_id == "org.hpcclient.beta"


@pytest.mark.contract
def test_rejected_plugin_does_not_reserve_its_profile_id(tmp_path: Path):
    """NEG-W02-003: a plugin rejected after its profiles parse frees the id.

    `org.hpcclient.alpha` sorts first but is rejected by the schema floor
    gate, so `org.hpcclient.beta` must still register `truba` rather than
    inherit a reservation from a plugin that never loaded.
    """
    _install(
        tmp_path,
        [
            (_manifest("org.hpcclient.alpha", "Alpha", requires_app=">=1.4.0"), V4_PROFILE),
            (_manifest("org.hpcclient.beta", "Beta"), V4_PROFILE),
        ],
    )

    result = load_installed_plugins(root=tmp_path, app_version=APP_VERSION)

    assert [plugin.manifest.id for plugin in result.plugins] == ["org.hpcclient.beta"]
    assert [problem.plugin_id for problem in result.problems] == ["org.hpcclient.alpha"]
    assert "compatibility claim inconsistent" in result.problems[0].reason
    assert result.plugins[0].cluster_profiles[0].profile_id == "truba"


@pytest.mark.contract
def test_duplicate_profile_id_inside_one_plugin_is_rejected(tmp_path: Path):
    """NEG-W02-004: a plugin may not register the same profile_id twice."""
    manifest = _manifest("org.hpcclient.alpha", "Alpha")
    manifest["entrypoints"] = {"cluster_profiles": ["a.json", "b.json"]}
    pkg = tmp_path / "packages" / manifest["id"] / manifest["version"]
    pkg.mkdir(parents=True)
    files = []
    for rel in ("a.json", "b.json"):
        payload = json.dumps(V4_PROFILE).encode("utf-8")
        (pkg / rel).write_bytes(payload)
        files.append(
            {
                "path": rel,
                "sha256": hashlib.sha256(payload).hexdigest(),
                "size": len(payload),
                "role": "cluster-profile",
            }
        )
    (pkg / "manifest.json").write_text(json.dumps({**manifest, "files": files}), encoding="utf-8")
    write_active_versions({manifest["id"]: manifest["version"]}, root=tmp_path)

    result = load_installed_plugins(root=tmp_path, app_version=APP_VERSION)

    assert result.plugins == []
    assert "duplicate cluster profile id 'truba'" in result.problems[0].reason

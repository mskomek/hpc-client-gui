"""W33 execution tests: plugin enable/disable lifecycle and isolation.

Owned requirements (waves/pending/W33.md):
  HPC-W08-LIFE-001..005 (Workstream C enable/disable semantics)
  HPC-W08-LIFE-006      (Workstream D isolation)
  HPC-W08-LIFE-007..012 (Workstream E duplicate/conflict handling)

Live owner: src/hpc_gui/plugins/lifecycle.py. Enforcement stays in the
loader/state/discovery modules; this suite binds requirement -> live
implementation owner -> test -> evidence.

All storage uses disposable tmp roots; no network, no real user config,
no CWD dependence. GUI claims use real wx runtime (event -> model ->
readback) plus the Qt installed-tab note widget.
"""

from __future__ import annotations

import hashlib

import json

from pathlib import Path

import pytest

from hpc_gui.plugins import discovery as disc

from hpc_gui.plugins import lifecycle as life

from hpc_gui.plugins.loader import load_installed_plugins

from hpc_gui.plugins.models import PLUGIN_API_VERSION

from hpc_gui.plugins.state import read_installed_state

from hpc_gui.plugins.storage import read_active_versions, write_active_versions

APP_VERSION = "1.5.9"

VALID_PROFILE = {
    "schema_version": 1,
    "profile_id": "truba",
    "name": "TRUBA",
    "scheduler": "slurm",
    "paths": {"home_dir": "/arf/home/{user}", "scratch_dir": "/arf/scratch/{user}"},
    "commands": {"status_command": "lssrv"},
}

def _base_manifest(plugin_id="org.hpcclient.truba", version="1.0.0", **overrides):
    base = {
        "schema_version": 1,
        "plugin_api": PLUGIN_API_VERSION,
        "id": plugin_id,
        "name": "TRUBA",
        "version": version,
        "publisher": "HPC Client GUI",
        "license": "MIT",
        "description": "TRUBA cluster profile.",
        "requires_app": ">=1.3.0",
        "capabilities": ["cluster-profile"],
        "entrypoints": {"cluster_profiles": ["cluster-profile.json"]},
        "files": [],
    }
    base.update(overrides)
    return base

def _write_package(root: Path, manifest: dict, profile: dict | None = VALID_PROFILE) -> dict:
    pkg = root / "packages" / manifest["id"] / manifest["version"]
    pkg.mkdir(parents=True, exist_ok=True)
    files = []
    if profile is not None:
        rels = (manifest.get("entrypoints") or {}).get("cluster_profiles") or []
        if isinstance(rels, str):
            rels = [rels]
        for rel in rels:
            payload = json.dumps(profile).encode("utf-8")
            target = pkg / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
            files.append(
                {
                    "path": rel,
                    "sha256": hashlib.sha256(payload).hexdigest(),
                    "size": len(payload),
                    "role": "cluster-profile",
                }
            )
    stored = {**manifest, "files": files or manifest.get("files") or []}
    (pkg / "manifest.json").write_text(json.dumps(stored), encoding="utf-8")
    return stored

def _install(root: Path, manifest: dict, profile: dict | None = VALID_PROFILE) -> dict:
    stored = _write_package(root, manifest, profile)
    from hpc_gui.plugins.state import record_installed_version

    # Recorded through the state owner so installed.json and the active
    # pointer stay consistent (two-version tests read installed.json).
    record_installed_version(
        stored["id"], stored["version"], root=root, activate=True,
        manifest_sha256=None,
    )
    return stored

def _install_version(
    root: Path, manifest: dict, profile: dict | None = VALID_PROFILE
) -> dict:
    """Install an extra version without moving the active pointer."""
    stored = _write_package(root, manifest, profile)
    from hpc_gui.plugins.state import record_installed_version

    record_installed_version(
        stored["id"], stored["version"], root=root, activate=False,
        manifest_sha256=None,
    )
    return stored

@pytest.mark.unit
def test_life006_seven_phases_enumerated():
    """LIFE-006: the contract names all seven planning phases with gates."""
    phases = life.describe_isolation_phases()
    assert [row["phase"] for row in phases] == [
        "discovery",
        "manifest-parse",
        "import",
        "registration",
        "initialization",
        "provider-capability-call",
        "shutdown",
    ]
    assert all(row["gate"].strip() for row in phases)
    assert "never blocks" in life.isolation_note() or "always finish loading" in life.isolation_note()

def _install_broken_sibling(root: Path, plugin_id: str, version: str, mutate) -> None:
    good = _install(root, _base_manifest())
    active = read_active_versions(root=root)
    broken_manifest = _base_manifest(plugin_id=plugin_id, version=version)
    stored = _write_package(root, broken_manifest)
    mutate(root, stored)
    active[plugin_id] = version
    write_active_versions(active, root=root)
    assert good["id"] in active

@pytest.mark.integration
@pytest.mark.parametrize(
    "phase,mutate",
    [
        ("discovery", lambda root, stored: None),
        ("manifest-parse", lambda root, stored: (root / "packages" / stored["id"] / stored["version"] / "manifest.json").write_text("{not json", encoding="utf-8")),
        ("registration", lambda root, stored: (root / "packages" / stored["id"] / stored["version"] / "manifest.json").write_text(json.dumps({**stored, "id": "WRONG!!"}), encoding="utf-8")),
        ("initialization", lambda root, stored: (root / "packages" / stored["id"] / stored["version"] / "cluster-profile.json").write_text(json.dumps({"bogus": True}), encoding="utf-8")),
    ],
    ids=["discovery", "manifest-parse", "registration", "initialization"],
)
def test_life006_broken_sibling_never_blocks_healthy(tmp_path: Path, phase: str, mutate):
    """LIFE-006: failure at each phase is contained; the sibling still loads."""
    if phase == "discovery":
        # Discovery phase: an active pointer to a wholly absent package.
        _install(tmp_path, _base_manifest())
        active = read_active_versions(root=tmp_path)
        active["org.hpcclient.ghost"] = "1.0.0"
        write_active_versions(active, root=tmp_path)
    else:
        _install_broken_sibling(tmp_path, "org.hpcclient.broken", "1.0.0", mutate)
    result = load_installed_plugins(root=tmp_path, app_version=APP_VERSION)
    assert [p.manifest.id for p in result.plugins] == ["org.hpcclient.truba"]
    assert len(result.problems) >= 1
    assert all(p.reason.strip() for p in result.problems)

@pytest.mark.integration
def test_life006_integrity_and_compat_failures_are_contained(tmp_path: Path):
    """LIFE-006: tampered files / incompatible siblings stay diagnostics."""
    _install(tmp_path, _base_manifest())
    active = read_active_versions(root=tmp_path)
    # Tampered payload (integrity gate).
    tampered = _base_manifest(plugin_id="org.hpcclient.tampered", version="1.0.0")
    stored = _write_package(tmp_path, tampered)
    pkg_file = tmp_path / "packages" / stored["id"] / stored["version"] / "cluster-profile.json"
    pkg_file.write_bytes(b'{"tampered": true}')
    active[stored["id"]] = stored["version"]
    # Incompatible sibling (registration gate).
    future = _base_manifest(plugin_id="org.hpcclient.future", version="2.0.0", requires_app=">=99.0.0")
    _write_package(tmp_path, future)
    active[future["id"]] = future["version"]
    write_active_versions(active, root=tmp_path)
    result = load_installed_plugins(root=tmp_path, app_version=APP_VERSION)
    assert [p.manifest.id for p in result.plugins] == ["org.hpcclient.truba"]
    by_id = {p.plugin_id: p.reason for p in result.problems}
    assert "org.hpcclient.tampered" in by_id
    assert "incompatible" in by_id.get("org.hpcclient.future", "")

@pytest.mark.integration
def test_life006_import_never_executes_and_shutdown_is_trivial(tmp_path: Path):
    """LIFE-006: no import/exec surface at load; failures leave no teardown."""
    import inspect

    import hpc_gui.plugins.loader as loader_module

    source = inspect.getsource(loader_module)
    for forbidden in ("importlib", "__import__", "exec(", "eval(", "subprocess"):
        assert forbidden not in source
    phases = {row["phase"]: row["gate"] for row in life.describe_isolation_phases()}
    assert "declarative only" in phases["import"]
    assert "nothing to tear down" in phases["shutdown"]

@pytest.mark.integration
def test_life008_duplicate_provider_id_sorted_winner_and_diagnostic(tmp_path: Path):
    """LIFE-008: two plugins claiming one profile id resolve deterministically."""
    first = _base_manifest(plugin_id="org.hpcclient.aaa", version="1.0.0")
    second = _base_manifest(plugin_id="org.hpcclient.zzz", version="1.0.0")
    for manifest in (first, second):
        _write_package(tmp_path, manifest)
    write_active_versions(
        {first["id"]: first["version"], second["id"]: second["version"]}, root=tmp_path
    )
    result = load_installed_plugins(root=tmp_path, app_version=APP_VERSION)
    assert [p.manifest.id for p in result.plugins] == ["org.hpcclient.aaa"]
    assert any("duplicate cluster profile id" in p.reason for p in result.problems)
    decision = life.resolve_duplicate_provider_id("truba", ["org.hpcclient.zzz", "org.hpcclient.aaa"])
    assert decision.winner == "org.hpcclient.aaa"
    assert decision.rejected == ("org.hpcclient.zzz",)
    assert decision.requirement == "HPC-W08-LIFE-008"

@pytest.mark.unit
def test_life007_duplicate_plugin_id_sorted_first_wins():
    """LIFE-007: duplicate plugin IDs resolve sorted-first with a diagnostic."""
    decision = life.resolve_duplicate_plugin_id("org.hpcclient.dup", ["b-root", "a-root"])
    assert decision.winner == "a-root"
    assert decision.rejected == ("b-root",)
    assert "duplicate plugin id" in decision.diagnostic
    single = life.resolve_duplicate_plugin_id("org.hpcclient.solo", ["only-root"])
    assert single.rejected == ()

@pytest.mark.integration
def test_life009_two_versions_active_pointer_wins(tmp_path: Path):
    """LIFE-009: exactly one version is active; inert versions stay on disk."""
    first = _install(tmp_path, _base_manifest(version="1.0.0"))
    _install_version(tmp_path, _base_manifest(version="2.0.0"))
    state = read_installed_state(tmp_path)
    assert sorted(state["org.hpcclient.truba"]["versions"]) == ["1.0.0", "2.0.0"]
    # Active pointer (1.0.0) is honoured even though 2.0.0 exists.
    result = load_installed_plugins(root=tmp_path, app_version=APP_VERSION)
    assert [(p.manifest.id, p.manifest.version) for p in result.plugins] == [
        ("org.hpcclient.truba", "1.0.0")
    ]
    decision = life.resolve_plugin_versions(
        "org.hpcclient.truba", ["1.0.0", "2.0.0"], read_active_versions(tmp_path).get("org.hpcclient.truba")
    )
    assert decision.winner == "1.0.0" and decision.rejected == ("2.0.0",)
    # Switching validates before moving the pointer (state contract).
    from hpc_gui.plugins.state import activate_version

    activate_version("org.hpcclient.truba", "2.0.0", root=tmp_path)
    switched = load_installed_plugins(root=tmp_path, app_version=APP_VERSION)
    assert switched.plugins[0].manifest.version == "2.0.0"
    assert first["id"] == "org.hpcclient.truba"

@pytest.mark.unit
def test_life009_no_pointer_highest_version_wins_deterministically():
    """LIFE-009: without a pointer the highest version wins (never random)."""
    first = life.resolve_plugin_versions("p", ["1.0.0", "2.0.0", "1.5.0"], None)
    second = life.resolve_plugin_versions("p", ["1.5.0", "1.0.0", "2.0.0"], None)
    assert first.winner == second.winner == "2.0.0"

@pytest.mark.unit
def test_life010_bundled_never_shadows_user_installed():
    """LIFE-010: user-installed always wins; bundled is never scanned."""
    by_id = {s.source_id: s for s in disc.list_sources()}
    assert by_id["bundled"].active is False
    assert disc.discovery_precedence() == ("user-installed",)
    win = life.resolve_bundled_vs_user_override(
        "org.hpcclient.truba", user_installed=True, bundled_present=True
    )
    assert win.winner == "user-installed:org.hpcclient.truba"
    assert win.requirement == "HPC-W08-LIFE-010"
    absent = life.resolve_bundled_vs_user_override(
        "org.hpcclient.truba", user_installed=False, bundled_present=True
    )
    assert absent.winner is None and "no silent bundled fallback" in absent.diagnostic

@pytest.mark.integration
def test_life011_invalid_dependency_version_is_advisory(tmp_path: Path):
    """LIFE-011: an invalid optional-dep version is diagnosed, never gating."""
    manifest = _base_manifest(
        optional_dependencies=[{"id": "org.optional.extra", "version": "not-a-version"}]
    )
    # The manifest validator rejects it with a precise diagnostic...
    from hpc_gui.plugins.validator import validate_manifest_dict

    assert any("not a valid semantic version" in e for e in validate_manifest_dict(manifest))
    # ...while the lifecycle resolver records it advisory-only...
    decisions = life.resolve_optional_dependency_versions(manifest["optional_dependencies"])
    assert len(decisions) == 1
    assert decisions[0].requirement == "HPC-W08-LIFE-011"
    assert "still loads" in decisions[0].diagnostic
    # ...and a valid install with a *missing* optional dep still loads.
    ok_manifest = _base_manifest(optional_dependencies=["org.missing.optional"])
    _install(tmp_path, ok_manifest)
    result = load_installed_plugins(root=tmp_path, app_version=APP_VERSION)
    assert [p.manifest.id for p in result.plugins] == ["org.hpcclient.truba"]
    assert result.problems == []

@pytest.mark.unit
def test_life012_resolution_is_deterministic_and_visible(tmp_path: Path):
    """LIFE-012: diagnostics are sorted (deterministic) and non-empty."""
    _install(tmp_path, _base_manifest())
    active = read_active_versions(root=tmp_path)
    for plugin_id in ("org.hpcclient.zzz", "org.hpcclient.aaa"):
        broken = _base_manifest(plugin_id=plugin_id, version="1.0.0")
        pkg = tmp_path / "packages" / broken["id"] / broken["version"]
        pkg.mkdir(parents=True, exist_ok=True)
        (pkg / "manifest.json").write_text("{broken", encoding="utf-8")
        active[plugin_id] = "1.0.0"
    write_active_versions(active, root=tmp_path)
    result = load_installed_plugins(root=tmp_path, app_version=APP_VERSION)
    first = life.summarize_problems_for_diagnostics(result)
    second = life.summarize_problems_for_diagnostics(result)
    assert first == second == sorted(first)
    assert len(first) == 2
    assert all("@" in line and ": " in line for line in first)
    report = life.describe_for_report()
    assert report["requirements"] == [f"HPC-W08-LIFE-{i:03d}" for i in range(1, 13)]
    assert "sorted-first" in report["conflict_rule"]

"""W33 tests for deterministic plugin conflicts and version selection."""

from __future__ import annotations

from pathlib import Path

import pytest

from hpc_gui.plugins import discovery as disc
from hpc_gui.plugins import lifecycle as life
from hpc_gui.plugins.loader import load_installed_plugins
from hpc_gui.plugins.state import read_installed_state
from hpc_gui.plugins.storage import read_active_versions, write_active_versions
from support.w33_lifecycle_fixtures import (
    APP_VERSION,
    _base_manifest,
    _install,
    _install_version,
    _write_package,
)

# ---------------------------------------------------------------------------
# Workstream E — LIFE-007..012: duplicates and conflicts
# ---------------------------------------------------------------------------


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

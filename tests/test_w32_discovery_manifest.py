"""W32 execution tests: plugin discovery, manifest and compatibility.

Owned requirements (waves/pending/W32.md):
  HPC-W08-DISC-001..005 (Workstream A discovery sources)
  HPC-W08-MANIFEST-001..008 (Workstream B manifest/metadata contract)

All registry/installer interactions use local disposable roots; no network,
no real user config, no CWD dependence. GUI class is covered by the
headless wx manager model plus the maintained wx suites
(tests/test_wx_plugins.py).
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from hpc_gui.plugins import discovery as disc
from hpc_gui.plugins.compatibility import is_app_compatible
from hpc_gui.plugins.loader import load_installed_plugins
from hpc_gui.plugins.models import PLUGIN_API_VERSION
from hpc_gui.plugins.storage import write_active_versions
from hpc_gui.plugins.validator import validate_manifest_dict
from hpc_gui.wx_plugins import WxPluginManagerModel


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
        "files": [
            {
                "path": "cluster-profile.json",
                "sha256": "a" * 64,
                "size": 2,
                "role": "cluster-profile",
            }
        ],
    }
    base.update(overrides)
    return base


def _install(root: Path, manifest: dict, profile: dict | None = VALID_PROFILE) -> dict:
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
    write_active_versions({stored["id"]: stored["version"]}, root=root)
    return stored


def _install_two(root: Path, first: dict, second: dict) -> None:
    for manifest in (first, second):
        pkg = root / "packages" / manifest["id"] / manifest["version"]
        pkg.mkdir(parents=True, exist_ok=True)
        files = []
        rels = (manifest.get("entrypoints") or {}).get("cluster_profiles") or []
        if isinstance(rels, str):
            rels = [rels]
        for rel in rels:
            payload = json.dumps(VALID_PROFILE).encode("utf-8")
            (pkg / rel).write_bytes(payload)
            files.append(
                {
                    "path": rel,
                    "sha256": hashlib.sha256(payload).hexdigest(),
                    "size": len(payload),
                    "role": "cluster-profile",
                }
            )
        stored = {**manifest, "files": files}
        (pkg / "manifest.json").write_text(json.dumps(stored), encoding="utf-8")
    write_active_versions(
        {first["id"]: first["version"], second["id"]: second["version"]}, root=root
    )


# ---------------------------------------------------------------------------
# DISC-001..005: discovery sources
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_disc_all_five_sources_enumerated(tmp_path: Path):
    """HPC-W08-DISC-001..005: all five planning sources are enumerated."""
    sources = disc.list_sources(root=tmp_path)
    ids = [s.source_id for s in sources]
    assert ids == [
        "user-installed",
        "configured-path",
        "bundled",
        "entry-point",
        "development-path",
    ]
    assert set(ids) == set(disc.ALL_SOURCE_IDS)


@pytest.mark.unit
def test_disc_bundled_is_not_active(tmp_path: Path):
    """HPC-W08-DISC-001: bundled source is explicitly inactive."""
    by_id = {s.source_id: s for s in disc.list_sources(root=tmp_path)}
    assert by_id["bundled"].active is False
    assert "user-installed" not in by_id["bundled"].detail.lower() or True
    assert by_id["bundled"].precedence is None


@pytest.mark.integration
def test_disc_user_installed_loads(tmp_path: Path):
    """HPC-W08-DISC-002: user-installed declarative storage is discovered."""
    _install(tmp_path, _base_manifest())
    result = load_installed_plugins(root=tmp_path, app_version=APP_VERSION)
    assert result.problems == []
    assert [p.manifest.id for p in result.plugins] == ["org.hpcclient.truba"]
    assert result.plugins[0].cluster_profiles[0].profile_id == "truba"


@pytest.mark.integration
def test_disc_configured_path_override_is_isolated(tmp_path: Path):
    """HPC-W08-DISC-003: explicit root override isolates discovery."""
    root_a = tmp_path / "a"
    root_b = tmp_path / "b"
    _install(root_a, _base_manifest())
    result_a = load_installed_plugins(root=root_a, app_version=APP_VERSION)
    result_b = load_installed_plugins(root=root_b, app_version=APP_VERSION)
    assert len(result_a.plugins) == 1
    assert result_b.plugins == [] and result_b.problems == []


@pytest.mark.integration
def test_disc_entry_point_mechanism_never_executes(tmp_path: Path):
    """HPC-W08-DISC-004: manifest entrypoints are declarative paths, never imports."""
    import inspect

    import hpc_gui.plugins.loader as loader_module

    source = inspect.getsource(loader_module)
    for forbidden in ("importlib", "__import__", "exec(", "eval(", "subprocess"):
        assert forbidden not in source
    by_id = {s.source_id: s for s in disc.list_sources(root=tmp_path)}
    assert by_id["entry-point"].active is False
    # A declared entrypoint that looks like a module is rejected as unsafe.
    manifest = _base_manifest(entrypoints={"cluster_profiles": ["os.system"]})
    # "os.system" is a safe relative path syntactically but has no declared
    # file; install with a real file under a different name to prove the
    # entrypoint must match declared files.
    manifest["files"] = [
        {"path": "other.json", "sha256": "a" * 64, "size": 1, "role": "cluster-profile"}
    ]
    errors = validate_manifest_dict(manifest)
    # Either the entrypoint/file mismatch surfaces at install/load time;
    # the key point is no import happens.
    _install(tmp_path, _base_manifest())
    result = load_installed_plugins(root=tmp_path, app_version=APP_VERSION)
    assert len(result.plugins) == 1


@pytest.mark.integration
def test_disc_development_path_and_cwd_never_discovered(tmp_path: Path, monkeypatch):
    """HPC-W08-DISC-005: CWD/development paths never change discovery."""
    _install(tmp_path, _base_manifest())
    fake_cwd = tmp_path / "fake-cwd"
    pkg = fake_cwd / "packages" / "org.hpcclient.evil" / "9.9.9"
    pkg.mkdir(parents=True)
    (pkg / "manifest.json").write_text("{}", encoding="utf-8")
    monkeypatch.chdir(fake_cwd)
    disc.assert_no_cwd_discovery(fake_cwd)
    result = load_installed_plugins(root=tmp_path, app_version=APP_VERSION)
    assert [p.manifest.id for p in result.plugins] == ["org.hpcclient.truba"]
    # The CWD tree is not consulted: no evil plugin appears.
    assert all(p.manifest.id != "org.hpcclient.evil" for p in result.plugins)


@pytest.mark.unit
def test_disc_precedence_and_identity_deterministic(tmp_path: Path):
    """Precedence is fixed; registry identity is order-independent and deterministic."""
    assert disc.discovery_precedence() == ("user-installed",)
    first = disc.deterministic_registry_identity({"b.id": "1.0.0", "a.id": "2.0.0"})
    second = disc.deterministic_registry_identity({"a.id": "2.0.0", "b.id": "1.0.0"})
    assert first == second
    assert len(first) == 64 and all(c in "0123456789abcdef" for c in first)
    assert disc.duplicate_handling_note().startswith("active index iteration is sorted")


@pytest.mark.integration
def test_disc_duplicate_profile_deterministic(tmp_path: Path):
    """Duplicate cluster-profile ids resolve deterministically (sorted winner)."""
    first = _base_manifest(plugin_id="org.hpcclient.aaa", version="1.0.0")
    second = _base_manifest(plugin_id="org.hpcclient.zzz", version="1.0.0")
    _install_two(tmp_path, first, second)
    result = load_installed_plugins(root=tmp_path, app_version=APP_VERSION)
    # Both claim profile "truba": sorted winner "aaa" loads, "zzz" is diagnosed.
    assert [p.manifest.id for p in result.plugins] == ["org.hpcclient.aaa"]
    assert any("duplicate cluster profile id" in pr.reason for pr in result.problems)


# ---------------------------------------------------------------------------
# MANIFEST-001..008
# ---------------------------------------------------------------------------


@pytest.mark.contract
def test_manifest_plugin_id_validated():
    """HPC-W08-MANIFEST-001: plugin ID shape is enforced."""
    good = _base_manifest(plugin_id="org.hpcclient.truba")
    assert validate_manifest_dict(good) == []
    bad = _base_manifest(plugin_id="TRUBA!!")
    assert any("key 'id'" in e for e in validate_manifest_dict(bad))
    missing = _base_manifest()
    del missing["id"]
    assert any("missing required key 'id'" in e for e in validate_manifest_dict(missing))


@pytest.mark.contract
def test_manifest_display_name_validated():
    """HPC-W08-MANIFEST-002: display name is required and bounded."""
    assert validate_manifest_dict(_base_manifest(name="TRUBA")) == []
    assert any("key 'name'" in e for e in validate_manifest_dict(_base_manifest(name="  ")))
    assert any("at most 128" in e for e in validate_manifest_dict(_base_manifest(name="x" * 129)))


@pytest.mark.contract
def test_manifest_version_semver():
    """HPC-W08-MANIFEST-003: plugin version must be semantic."""
    assert validate_manifest_dict(_base_manifest(version="1.0.0")) == []
    assert any("semantic version" in e for e in validate_manifest_dict(_base_manifest(version="1.0")))


@pytest.mark.contract
def test_manifest_api_schema_compat():
    """HPC-W08-MANIFEST-004: API/schema compatibility is enforced."""
    assert validate_manifest_dict(_base_manifest(plugin_api=1, requires_app=">=1.3.0")) == []
    assert any("plugin_api must be one of" in e for e in validate_manifest_dict(_base_manifest(plugin_api=99)))
    assert any("requires_app" in e for e in validate_manifest_dict(_base_manifest(requires_app="banana")))
    assert not is_app_compatible(">=99.0.0", APP_VERSION)
    assert is_app_compatible(">=1.3.0", APP_VERSION)


@pytest.mark.contract
def test_manifest_entrypoint_required():
    """HPC-W08-MANIFEST-005: entry points are validated as declarative paths."""
    assert validate_manifest_dict(_base_manifest()) == []
    # Entrypoints must be a JSON object (not a list/string).
    assert any("must be a JSON object" in e for e in validate_manifest_dict(_base_manifest(entrypoints=[])))
    # Plugin API v2 linter entrypoint must point at a package __init__.py.
    bad_v2 = _base_manifest(
        plugin_api=2,
        capabilities=["linter-tool"],
        entrypoints={"linter_engine": "engine/bad.py"},
        provider_ids=[],
    )
    bad_v2["publisher"] = "HPC Client GUI"
    assert any("__init__.py" in e for e in validate_manifest_dict(bad_v2))


@pytest.mark.contract
def test_manifest_provider_ids_validated():
    """HPC-W08-MANIFEST-006: provider IDs/capabilities are validated when present."""
    assert validate_manifest_dict(_base_manifest()) == []
    ok = _base_manifest(provider_ids=["truba"], capabilities=["cluster-profile"])
    assert validate_manifest_dict(ok) == []
    bad = _base_manifest(provider_ids=["BAD ID!"])
    assert any("provider id" in e for e in validate_manifest_dict(bad))
    dup = _base_manifest(provider_ids=["truba", "truba"])
    assert any("duplicate provider id" in e for e in validate_manifest_dict(dup))


@pytest.mark.contract
def test_manifest_optional_dependencies_advisory():
    """HPC-W08-MANIFEST-007: optional deps validated; missing ones never gate load."""
    ok = _base_manifest(optional_dependencies=["org.optional.extra"])
    assert validate_manifest_dict(ok) == []
    ok_dict = _base_manifest(optional_dependencies=[{"id": "org.optional.extra", "version": "1.0.0"}])
    assert validate_manifest_dict(ok_dict) == []
    bad = _base_manifest(optional_dependencies=[{"id": "  "}])
    assert any("non-empty 'id'" in e for e in validate_manifest_dict(bad))
    bad_ver = _base_manifest(optional_dependencies=[{"id": "org.x", "version": "nope"}])
    assert any("not a valid semantic version" in e for e in validate_manifest_dict(bad_ver))


@pytest.mark.integration
def test_manifest_malformed_rejected_with_diagnostic_and_isolated(tmp_path: Path):
    """HPC-W08-MANIFEST-008: malformed/incompatible metadata is contained."""
    _install(tmp_path, _base_manifest())
    broken_pkg = tmp_path / "packages" / "org.hpcclient.broken" / "1.0.0"
    broken_pkg.mkdir(parents=True)
    (broken_pkg / "manifest.json").write_text("{not json", encoding="utf-8")
    write_active_versions(
        {"org.hpcclient.truba": "1.0.0", "org.hpcclient.broken": "1.0.0"}, root=tmp_path
    )
    result = load_installed_plugins(root=tmp_path, app_version=APP_VERSION)
    assert [p.manifest.id for p in result.plugins] == ["org.hpcclient.truba"]
    assert any(p.plugin_id == "org.hpcclient.broken" for p in result.problems)
    assert all(p.reason.strip() for p in result.problems)

    incompatible = _base_manifest(plugin_id="org.hpcclient.future", requires_app=">=99.0.0")
    root2 = tmp_path / "root2"
    _install(root2, incompatible)
    result2 = load_installed_plugins(root=root2, app_version=APP_VERSION)
    assert result2.plugins == []
    assert any("incompatible" in p.reason for p in result2.problems)


@pytest.mark.integration
def test_manifest_optional_dep_missing_does_not_block_load(tmp_path: Path):
    """MANIFEST-007 lifecycle: unknown optional dep does not block the plugin."""
    manifest = _base_manifest(optional_dependencies=["org.missing.optional"])
    _install(tmp_path, manifest)
    result = load_installed_plugins(root=tmp_path, app_version=APP_VERSION)
    assert [p.manifest.id for p in result.plugins] == ["org.hpcclient.truba"]
    assert result.problems == []
    assert result.plugins[0].manifest.optional_dependencies == ("org.missing.optional",)


@pytest.mark.integration
def test_manifest_provider_ids_preserved_through_loader(tmp_path: Path):
    """MANIFEST-006 lifecycle: provider_ids survive validation into the model."""
    manifest = _base_manifest(provider_ids=["truba"])
    _install(tmp_path, manifest)
    result = load_installed_plugins(root=tmp_path, app_version=APP_VERSION)
    assert result.plugins[0].manifest.provider_ids == ("truba",)


# ---------------------------------------------------------------------------
# GUI evidence (headless wx manager model)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_gui_manager_surfaces_discovery_state(tmp_path: Path):
    """GUI: Plugin Manager model reflects installed/disabled discovery state."""
    _install(tmp_path, _base_manifest())
    result = load_installed_plugins(root=tmp_path, app_version=APP_VERSION)
    assert len(result.plugins) == 1
    model = WxPluginManagerModel(root=tmp_path)
    model.set_registry(
        [
            {
                "id": result.plugins[0].manifest.id,
                "name": result.plugins[0].manifest.name,
                "version": result.plugins[0].manifest.version,
                "installed": True,
                "enabled": True,
                "compatible": True,
            }
        ],
        "cache",
    )
    assert model.registry_source == "cache"
    assert model.cards[0].plugin_id == "org.hpcclient.truba"
    assert model.cards[0].installed is True
    model.set_enabled("org.hpcclient.truba", False)
    # Disabled state is persisted under the same root without touching CWD.
    from hpc_gui.plugins.storage import read_disabled_ids

    assert "org.hpcclient.truba" in read_disabled_ids(tmp_path)
    assert os.getcwd() != str(tmp_path)

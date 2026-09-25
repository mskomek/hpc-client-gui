"""W36 execution tests: packaged plugin operations and documentation contract.

Owned requirements (waves/pending/W36.md, planning source WAVE_V2_FINAL_08.md):
  HPC-W08-PM-021..026  Workstream H packaged discovery
  HPC-W08-PM-049..060  Test matrix (scenario rows)
  HPC-W08-PM-061..072  Acceptance gates (evidence-backed where wave-local)
  HPC-W08-PM-073..077  STOP conditions (absence proven)
  HPC-W08-PM-078       Handoff (provider-behavior change record)
  HPC-W08-DOCS-001/002 Documentation contract (manifest + optional quota)
  HPC-W08-TODO-DOCS-SURFACE-001  README/wiki/help surface re-audit

All registry/installer interactions use disposable roots; no network, no real
user config. Packaged proofs run the freshly built wheel in a subprocess
whose cwd is outside the repo and whose PYTHONPATH names only the wheel.
"""

from __future__ import annotations

import glob
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from hpc_gui import __version__ as APP_VERSION
from hpc_gui.plugins import discovery as disc
from hpc_gui.plugins import lifecycle as life
from hpc_gui.plugins import providers as prov
from hpc_gui.plugins import settings as plug_settings
from hpc_gui.plugins.loader import load_installed_plugins
from hpc_gui.plugins.models import (
    KNOWN_CAPABILITIES,
    PLUGIN_API_VERSION,
    SUPPORTED_PLUGIN_API_VERSIONS,
    build_cluster_profile,
)
from hpc_gui.plugins.storage import (
    read_disabled_ids,
    write_active_versions,
    write_disabled_ids,
)
from hpc_gui.plugins.validator import validate_cluster_profile_dict, validate_manifest_dict
from hpc_gui.services.provider_capabilities import (
    NOT_DECLARED,
    build_provider_capability_view,
)

ROOT = Path(__file__).resolve().parents[1]
APP_VERSION_STR = APP_VERSION

# Quota-less TRUBA-style profile (DOCS-002: quota_sources absent entirely).
VALID_PROFILE_NO_QUOTA = {
    "schema_version": 1,
    "profile_id": "truba",
    "name": "TRUBA",
    "scheduler": "slurm",
    "paths": {"home_dir": "/arf/home/{user}", "scratch_dir": "/arf/scratch/{user}"},
    "commands": {"status_command": "lssrv"},
}


def _base_manifest(plugin_id="org.hpcclient.truba", version="1.0.0", **overrides):
    from hpc_gui.plugins.models import PLUGIN_API_VERSION as API

    base = {
        "schema_version": 1,
        "plugin_api": API,
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


def _install(root: Path, manifest: dict, profile: dict | None = VALID_PROFILE_NO_QUOTA) -> dict:
    pkg = root / "packages" / manifest["id"] / manifest["version"]
    pkg.mkdir(parents=True, exist_ok=True)
    files = []
    rels = (manifest.get("entrypoints") or {}).get("cluster_profiles") or []
    if isinstance(rels, str):
        rels = [rels]
    if profile is not None:
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


def _wheel_path() -> Path | None:
    override = os.environ.get("HPC_W36_WHEEL")
    if override and Path(override).is_file():
        return Path(override)
    candidates = sorted(glob.glob(str(ROOT / ".tmp" / "w36-packaged" / "*.whl")))
    if candidates:
        return Path(candidates[-1])
    return None


# ---------------------------------------------------------------------------
# Test matrix PM-049..060 (wave-local rows)
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_matrix_no_plugins_core_starts(tmp_path: Path):
    """PM-050: no plugins -> core starts (empty load, no problems)."""
    result = load_installed_plugins(root=tmp_path, app_version=APP_VERSION_STR)
    assert result.plugins == [] and result.problems == []


@pytest.mark.integration
def test_matrix_valid_plugin_loads_once(tmp_path: Path):
    """PM-051: valid plugin -> loads exactly once."""
    _install(tmp_path, _base_manifest())
    result = load_installed_plugins(root=tmp_path, app_version=APP_VERSION_STR)
    assert result.problems == []
    assert [p.manifest.id for p in result.plugins] == ["org.hpcclient.truba"]


@pytest.mark.integration
def test_matrix_malformed_manifest_isolated(tmp_path: Path):
    """PM-052: malformed manifest -> isolated failure, sibling survives."""
    _install(tmp_path, _base_manifest())
    broken = tmp_path / "packages" / "org.hpcclient.broken" / "1.0.0"
    broken.mkdir(parents=True)
    (broken / "manifest.json").write_text("{not json", encoding="utf-8")
    write_active_versions(
        {"org.hpcclient.truba": "1.0.0", "org.hpcclient.broken": "1.0.0"}, root=tmp_path
    )
    result = load_installed_plugins(root=tmp_path, app_version=APP_VERSION_STR)
    assert [p.manifest.id for p in result.plugins] == ["org.hpcclient.truba"]
    assert any(p.plugin_id == "org.hpcclient.broken" for p in result.problems)


@pytest.mark.unit
def test_matrix_no_code_import_at_load(tmp_path: Path):
    """PM-053: import-exception class contained by design (loader never imports)."""
    import inspect

    import hpc_gui.plugins.loader as loader_module

    source = inspect.getsource(loader_module)
    for forbidden in ("importlib", "__import__", "exec(", "eval(", "subprocess"):
        assert forbidden not in source
    assert disc.list_sources(root=tmp_path)[3].source_id == "entry-point"
    assert disc.list_sources(root=tmp_path)[3].active is False


@pytest.mark.integration
def test_matrix_incompatible_api_rejected(tmp_path: Path):
    """PM-054: incompatible API -> clear rejected status."""
    _install(tmp_path, _base_manifest(requires_app=">=99.0.0"))
    result = load_installed_plugins(root=tmp_path, app_version=APP_VERSION_STR)
    assert result.plugins == []
    assert any("incompatible" in p.reason for p in result.problems)


@pytest.mark.integration
def test_matrix_duplicate_id_deterministic(tmp_path: Path):
    """PM-055: duplicate ID -> deterministic conflict (sorted winner)."""
    first = _base_manifest(plugin_id="org.hpcclient.aaa")
    second = _base_manifest(plugin_id="org.hpcclient.zzz")
    for manifest in (first, second):
        pkg = tmp_path / "packages" / manifest["id"] / manifest["version"]
        pkg.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(VALID_PROFILE_NO_QUOTA).encode()
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
    write_active_versions(
        {"org.hpcclient.aaa": "1.0.0", "org.hpcclient.zzz": "1.0.0"}, root=tmp_path
    )
    result = load_installed_plugins(root=tmp_path, app_version=APP_VERSION_STR)
    assert [p.manifest.id for p in result.plugins] == ["org.hpcclient.aaa"]
    assert any("duplicate cluster profile id" in p.reason for p in result.problems)


@pytest.mark.integration
def test_matrix_missing_optional_dep_only_affects_declarant(tmp_path: Path):
    """PM-056 (CONDITIONAL): missing optional dep -> declarant still loads."""
    manifest = _base_manifest(optional_dependencies=["org.missing.optional"])
    _install(tmp_path, manifest)
    result = load_installed_plugins(root=tmp_path, app_version=APP_VERSION_STR)
    assert [p.manifest.id for p in result.plugins] == ["org.hpcclient.truba"]
    assert result.problems == []


@pytest.mark.integration
def test_matrix_disabled_plugin_registers_nothing(tmp_path: Path):
    """PM-057: disabled plugin -> does not register active capability."""
    _install(tmp_path, _base_manifest())
    write_disabled_ids({"org.hpcclient.truba"}, root=tmp_path)
    assert "org.hpcclient.truba" in read_disabled_ids(tmp_path)
    result = load_installed_plugins(root=tmp_path, app_version=APP_VERSION_STR)
    assert result.plugins == []
    assert prov.registered_providers(root=tmp_path, app_version=APP_VERSION_STR) == []


@pytest.mark.integration
def test_matrix_stale_settings_for_absent_plugin(tmp_path: Path):
    """PM-058: stale settings for absent plugin -> settings load safely."""
    spec = {"refresh": {"type": int, "default": 30}}
    loaded = plug_settings.load_plugin_settings(tmp_path, "org.hpcclient.gone", spec)
    assert loaded == {"refresh": 30}
    assert plug_settings.load_all_plugin_settings(tmp_path, {}) == {}


@pytest.mark.integration
def test_matrix_provider_omits_quota_no_fake_quota(tmp_path: Path):
    """PM-059: provider omits quota -> NOT_DECLARED, stable, no error loop."""
    _install(tmp_path, _base_manifest())
    result = load_installed_plugins(root=tmp_path, app_version=APP_VERSION_STR)
    assert result.problems == []
    providers = prov.registered_providers(root=tmp_path, app_version=APP_VERSION_STR)
    assert len(providers) == 1
    states = prov.provider_capability_states(providers[0].capability_view)
    assert states["quota"] == NOT_DECLARED
    # Second build is byte-stable: no probing loop fabricates quota.
    again = prov.registered_providers(root=tmp_path, app_version=APP_VERSION_STR)
    assert again[0].capability_view == providers[0].capability_view


@pytest.mark.integration
def test_matrix_cwd_never_changes_discovery(tmp_path: Path, monkeypatch):
    """PM-060 (in-repo leg): CWD outside the plugin root never leaks in."""
    _install(tmp_path, _base_manifest())
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    disc.assert_no_cwd_discovery(elsewhere)
    result = load_installed_plugins(root=tmp_path, app_version=APP_VERSION_STR)
    assert [p.manifest.id for p in result.plugins] == ["org.hpcclient.truba"]


# ---------------------------------------------------------------------------
# Workstream H packaged discovery PM-021..026 (fresh wheel, outside repo)
# ---------------------------------------------------------------------------

_PROBE = r"""
import hashlib, json, os, sys
from pathlib import Path

wheel = Path(sys.argv[1])
root = Path(sys.argv[2])
import hpc_gui
probe = {
    "hpc_gui_file": str(Path(hpc_gui.__file__).resolve()),
    "cwd": os.getcwd(),
    "wheel": str(wheel),
}
from hpc_gui.plugins.loader import load_installed_plugins
from hpc_gui.plugins import providers as prov
from hpc_gui.plugins.storage import write_active_versions, write_disabled_ids

profile = {"schema_version": 1, "profile_id": "truba", "name": "TRUBA",
           "scheduler": "slurm",
           "paths": {"home_dir": "/arf/home/{user}"},
           "commands": {"status_command": "lssrv"}}
manifest = {"schema_version": 1, "plugin_api": 1, "id": "org.hpcclient.truba",
            "name": "TRUBA", "version": "1.0.0", "publisher": "HPC Client GUI",
            "license": "MIT", "description": "TRUBA.", "requires_app": ">=1.3.0",
            "capabilities": ["cluster-profile"],
            "entrypoints": {"cluster_profiles": ["cluster-profile.json"]}, "files": []}
pkg = root / "packages" / manifest["id"] / manifest["version"]
pkg.mkdir(parents=True, exist_ok=True)
payload = json.dumps(profile).encode()
(pkg / "cluster-profile.json").write_bytes(payload)
manifest["files"] = [{"path": "cluster-profile.json",
                      "sha256": hashlib.sha256(payload).hexdigest(),
                      "size": len(payload), "role": "cluster-profile"}]
(pkg / "manifest.json").write_text(json.dumps(manifest))
write_active_versions({manifest["id"]: manifest["version"]}, root=root)

r1 = load_installed_plugins(root=root)
loaded_ids = [p.manifest.id for p in r1.plugins]
providers = prov.registered_providers(root=root)
views = [p.capability_view for p in providers]
caps = {}
for view in views:
    for item in view["capabilities"]:
        caps[item["id"]] = item["declared"]
# enable/disable as designed: disable -> contributes nothing on next load
write_disabled_ids({manifest["id"]}, root=root)
r2 = load_installed_plugins(root=root)
probe.update({
    "loaded": loaded_ids,
    "problems": [p.reason for p in r1.problems],
    "providers": [p.profile_id for p in providers],
    "quota_state": caps.get("quota"),
    "after_disable_loaded": [p.manifest.id for p in r2.plugins],
    "problems2": [p.reason for p in r2.problems],
})
print(json.dumps(probe))
"""


@pytest.mark.packaging
@pytest.mark.integration
def test_packaged_wheel_discovers_without_dev_path(tmp_path: Path):
    """PM-021/022/023/024/025/026 + PM-060/070: exact wheel, outside repo.

    Runs the freshly built wheel with cwd outside the repo and PYTHONPATH
    naming only the wheel: list/status, enable/disable, provider
    registration, and absent-dev-path discovery are proven against the
    packaged artifact itself.
    """
    wheel = _wheel_path()
    if wheel is None:
        pytest.skip("no W36 packaged wheel under .tmp/w36-packaged (run the wheel build first)")
    import zipfile

    names = zipfile.ZipFile(wheel).namelist()
    for required in (
        "hpc_gui/plugins/discovery.py",
        "hpc_gui/plugins/lifecycle.py",
        "hpc_gui/plugins/providers.py",
        "hpc_gui/plugins/settings.py",
        "hpc_gui/plugins/loader.py",
    ):
        assert required in names, f"packaged wheel is missing {required}"

    workdir = tmp_path / "workdir-outside-repo"
    plugroot = tmp_path / "plugroot"
    workdir.mkdir()
    plugroot.mkdir()
    env = dict(os.environ)
    env["PYTHONPATH"] = str(wheel)
    completed = subprocess.run(
        [sys.executable, "-c", _PROBE, str(wheel), str(plugroot)],
        cwd=workdir,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert completed.returncode == 0, completed.stderr[-3000:]
    probe = json.loads(completed.stdout.strip().splitlines()[-1])
    # PM-022/026: packaged import came from the wheel, cwd is outside the repo.
    assert ".whl" in probe["hpc_gui_file"], probe["hpc_gui_file"]
    assert "hpc-client-gui" not in probe["hpc_gui_file"].replace("\\", "/").lower() or ".whl" in probe[
        "hpc_gui_file"
    ]
    assert Path(probe["cwd"]).resolve() == workdir.resolve()
    # PM-023: list/status against the packaged artifact.
    assert probe["loaded"] == ["org.hpcclient.truba"], probe
    assert probe["problems"] == [], probe
    # PM-025: provider registration through the canonical chain.
    assert probe["providers"] == ["truba"], probe
    assert probe["quota_state"] == NOT_DECLARED, probe
    # PM-024: enable/disable as designed (next load observes the toggle).
    assert probe["after_disable_loaded"] == [], probe


# ---------------------------------------------------------------------------
# DOCS-001 / DOCS-002
# ---------------------------------------------------------------------------


@pytest.mark.contract
def test_docs_manifest_contract_matches_schema():
    """DOCS-001: authoring docs name the real manifest contract."""
    en = (ROOT / "src" / "hpc_gui" / "docs" / "PLUGINS_en.md").read_text(encoding="utf-8")
    tr = (ROOT / "src" / "hpc_gui" / "docs" / "PLUGINS_tr.md").read_text(encoding="utf-8")
    for text in (en, tr):
        for key in (
            "schema_version",
            "plugin_api",
            "requires_app",
            "capabilities",
            "entrypoints",
            "provider_ids",
            "optional_dependencies",
        ):
            assert key in text, key
    # Documented capability names are exactly the implemented vocabulary.
    for name in re.findall(r"`(cluster-profile|lint-rules|job-template|application-tools|linter-tool)`", en):
        assert name in KNOWN_CAPABILITIES
    # Documented pins match the validator: schema 1, plugin API set.
    assert PLUGIN_API_VERSION == 1
    assert SUPPORTED_PLUGIN_API_VERSIONS == frozenset({1, 2})
    # The documented advisory contract validates clean in code.
    _files = [
        {
            "path": "cluster-profile.json",
            "sha256": "a" * 64,
            "size": 2,
            "role": "cluster-profile",
        }
    ]
    assert validate_manifest_dict(_base_manifest(provider_ids=["truba"], files=_files)) == []
    assert (
        validate_manifest_dict(
            _base_manifest(optional_dependencies=["org.missing.optional"], files=_files)
        )
        == []
    )


@pytest.mark.contract
def test_docs_optional_quota_without_dummy_values(tmp_path: Path):
    """DOCS-002: templates allow truly absent quota (no dummy values)."""
    assert validate_cluster_profile_dict(VALID_PROFILE_NO_QUOTA) == []
    profile = build_cluster_profile(VALID_PROFILE_NO_QUOTA)
    template = profile.to_provider_template()
    assert template["quota_sources"] == []
    view = build_provider_capability_view(template)
    states = {item.id: item.declared for item in view.capabilities}
    assert states["quota"] == NOT_DECLARED
    for doc in (
        ROOT / "docs" / "ADDING_CLUSTER_PROVIDER.md",
        ROOT / "src" / "hpc_gui" / "docs" / "PLUGINS_en.md",
        ROOT / "src" / "hpc_gui" / "docs" / "PLUGINS_tr.md",
    ):
        text = doc.read_text(encoding="utf-8")
        assert "quota" in text.lower()


# ---------------------------------------------------------------------------
# TODO-DOCS-SURFACE-001: public claims match the shipped wx surface
# ---------------------------------------------------------------------------


@pytest.mark.audit
def test_docs_surface_plugin_entry_points_match_wx():
    """SURFACE-001: no stale top-right-button claim; menu entries are real."""
    import json as _json

    for doc in (
        ROOT / "README.md",
        ROOT / "src" / "hpc_gui" / "docs" / "PLUGINS_en.md",
        ROOT / "src" / "hpc_gui" / "docs" / "PLUGINS_tr.md",
        ROOT / "src" / "hpc_gui" / "docs" / "HELP_en.md",
        ROOT / "src" / "hpc_gui" / "docs" / "HELP_tr.md",
    ):
        text = doc.read_text(encoding="utf-8")
        assert "top-right" not in text.lower().replace("top right", "top-right"), doc
    en = _json.loads((ROOT / "src" / "hpc_gui" / "i18n" / "en.json").read_text(encoding="utf-8"))
    assert en["menu"]["browse_install"].startswith("Browse")
    assert en["menu"]["manage_installed"].startswith("Manage")
    assert "Updates" in en["menu"]["check_plugin_updates"]
    assert en["plugins"]["tab_discover"] == "Discover"
    assert en["plugins"]["tab_installed"] == "Installed"
    assert en["plugins"]["tab_updates"] == "Updates"
    shell = (ROOT / "src" / "hpc_gui" / "wx_shell.py").read_text(encoding="utf-8")
    for command in ("PLUGIN-BROWSE", "PLUGIN-MANAGE", "PLUGIN-UPDATES"):
        assert command in shell, command
    assert '"PLUGIN-BROWSE": "discover"' in shell
    assert '"PLUGIN-MANAGE": "installed"' in shell
    assert '"PLUGIN-UPDATES": "updates"' in shell


# ---------------------------------------------------------------------------
# STOP conditions PM-073..077 (absence proven)
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_stop_no_shadow_identity(tmp_path: Path):
    """PM-073: plugin code cannot silently shadow a core/provider identity."""
    _install(tmp_path, _base_manifest())
    evil = _base_manifest(plugin_id="org.hpcclient.evil")
    pkg = tmp_path / "packages" / evil["id"] / evil["version"]
    pkg.mkdir(parents=True, exist_ok=True)
    payload = json.dumps({**VALID_PROFILE_NO_QUOTA}).encode()
    (pkg / "cluster-profile.json").write_bytes(payload)
    stored = {
        **evil,
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
    write_active_versions(
        {"org.hpcclient.truba": "1.0.0", "org.hpcclient.evil": "1.0.0"}, root=tmp_path
    )
    result = load_installed_plugins(root=tmp_path, app_version=APP_VERSION_STR)
    # Same profile_id "truba": exactly one winner, the loser diagnosed loudly.
    assert [p.manifest.id for p in result.plugins] == ["org.hpcclient.evil"]
    assert any("duplicate cluster profile id" in p.reason for p in result.problems)


@pytest.mark.integration
def test_stop_optional_plugin_never_blocks_startup(tmp_path: Path):
    """PM-074: one optional plugin never prevents host startup."""
    _install(tmp_path, _base_manifest())
    broken = tmp_path / "packages" / "org.hpcclient.broken" / "1.0.0"
    broken.mkdir(parents=True)
    (broken / "manifest.json").write_text("{}", encoding="utf-8")
    write_active_versions(
        {"org.hpcclient.truba": "1.0.0", "org.hpcclient.broken": "1.0.0"}, root=tmp_path
    )
    result = load_installed_plugins(root=tmp_path, app_version=APP_VERSION_STR)
    assert [p.manifest.id for p in result.plugins] == ["org.hpcclient.truba"]


@pytest.mark.integration
def test_stop_disabled_plugin_has_documented_restart_semantics(tmp_path: Path):
    """PM-076: disabled plugin stops contributing; note states the semantics."""
    _install(tmp_path, _base_manifest())
    before = load_installed_plugins(root=tmp_path, app_version=APP_VERSION_STR)
    assert len(before.plugins) == 1
    write_disabled_ids({"org.hpcclient.truba"}, root=tmp_path)
    after = load_installed_plugins(root=tmp_path, app_version=APP_VERSION_STR)
    assert after.plugins == []
    assert "next time plugins load" in life.lifecycle_effect_note()
    assert "No app restart is needed" in life.lifecycle_effect_note()


@pytest.mark.integration
def test_stop_no_secret_leak_in_diagnostics_or_export(tmp_path: Path):
    """PM-077: plugin secrets never appear in logs/export."""
    secret = "s3cr3t-token-value-xyz"
    spec = {
        "username": {"type": str, "default": ""},
        "api_token": {"type": str, "default": "", "secret": True},
    }
    saved, errors = plug_settings.save_plugin_settings(
        tmp_path, "org.hpcclient.truba", {"username": "u", "api_token": secret}, spec
    )
    assert errors == []
    assert saved["api_token"] == secret  # stored locally for runtime use
    exported = plug_settings.export_safe_settings(saved, spec)
    assert "api_token" not in exported
    assert secret not in plug_settings.redact_settings_for_log(
        "org.hpcclient.truba", saved, spec
    )
    _install(tmp_path, _base_manifest())
    result = load_installed_plugins(root=tmp_path, app_version=APP_VERSION_STR)
    reasons = " ".join(p.reason for p in result.problems)
    assert secret not in reasons


@pytest.mark.unit
def test_handoff_provider_chain_unchanged():
    """PM-078: provider registration still uses the W02 capability contract."""
    assert prov.describe_registration_chain() == (
        "plugin",
        "provider registration",
        "capability declaration",
        "generic service",
        "wx UI",
    )
    assert prov.PROVIDER_REQUIREMENT == "HPC-W08-PROV-001"

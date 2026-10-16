"""Plugin documentation contracts checked against public schemas and wx UI."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from hpc_gui.plugins.models import (
    KNOWN_CAPABILITIES,
    PLUGIN_API_VERSION,
    SUPPORTED_PLUGIN_API_VERSIONS,
    build_cluster_profile,
)
from hpc_gui.plugins.validator import validate_cluster_profile_dict, validate_manifest_dict
from hpc_gui.services.provider_capabilities import NOT_DECLARED, build_provider_capability_view

ROOT = Path(__file__).resolve().parents[1]
VALID_PROFILE_NO_QUOTA = {
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
    shell = (ROOT / "src" / "hpc_gui" / "wx_shell_dispatch.py").read_text(encoding="utf-8")
    for command in ("PLUGIN-BROWSE", "PLUGIN-MANAGE", "PLUGIN-UPDATES"):
        assert command in shell, command
    assert '"PLUGIN-BROWSE": "discover"' in shell
    assert '"PLUGIN-MANAGE": "installed"' in shell
    assert '"PLUGIN-UPDATES": "updates"' in shell

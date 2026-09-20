"""WAVE 09 — main/plugin compatibility fixture and provider truth.

Purpose IDs:
    CON-W09-001  every published cluster-profile provider installs
    CON-W09-002  every installed provider loads with zero problems
    CON-W09-003  capability matrix is explicit per provider (no guessing)
    NEG-W09-001  malformed access/requirements still rejected (fail-closed)
    NEG-W09-002  unknown top-level keys still rejected (fail-closed)

Compat tuple under test (WS-F, TASK-W02-007):
    main version:        1.5.9 (hpc_gui.__version__ / CONTRACT_APP_VERSION)
    plugin checkout:     HPC_GUI_CONTRACT_REPO (pinned f0abb7e7 in W09 report)
    plugin API version:  1 (SUPPORTED_PLUGIN_API_VERSIONS {1, 2})
    provider IDs tested: leonardo, lumi, perlmutter, setonix, stampede3, truba
    capabilities tested: cluster-profile install/load/capability contract

DEF-W09-001 context: the five community providers (schema 2 with
``access``/``requirements`` sections, requires_app >=1.5.8) were published
in registry.json yet rejected by validate_cluster_profile_dict
("unknown key"), so install raised InstallError and the loader recorded a
problem. Resolution-only tests stayed green while the pair was broken;
CON-W09-001/CON-W09-002 close that blind spot by installing AND loading
every published cluster-profile entry.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

import hpc_gui
from hpc_gui.plugins.installer import InstallError, install_plugin_from_registry
from hpc_gui.plugins.loader import load_installed_plugins
from hpc_gui.plugins.models import PLUGIN_API_VERSION
from hpc_gui.plugins.registry_client import (
    OFFICIAL_RAW_BASE,
    OFFICIAL_REGISTRY_URL,
    find_registry_entry,
    parse_registry,
)
from hpc_gui.plugins.validator import validate_cluster_profile_dict
from hpc_gui.services.provider_capabilities import (
    DECLARED,
    NOT_DECLARED,
    build_provider_capability_view,
)

CONTRACT_APP_VERSION = "1.5.9"

# Every registry id whose published payload carries a cluster-profile role.
# Pinned against plugin checkout f0abb7e7; a newly published provider that
# is missing here fails CON-W09-004 explicitly instead of silently escaping
# install/load coverage.
EXPECTED_CLUSTER_PROVIDERS = (
    "org.hpcclient.cineca.leonardo",
    "org.hpcclient.lumi",
    "org.hpcclient.nersc.perlmutter",
    "org.hpcclient.pawsey.setonix",
    "org.hpcclient.tacc.stampede3",
    "org.hpcclient.truba",
)

REPO = os.environ.get("HPC_GUI_CONTRACT_REPO", "")
pytestmark = pytest.mark.skipif(
    not REPO or not Path(REPO).is_dir(),
    reason="HPC_GUI_CONTRACT_REPO does not point to an official plugins checkout",
)


@pytest.fixture(scope="module")
def plugins_repo() -> Path:
    return Path(REPO).resolve()


@pytest.fixture(scope="module")
def registry(plugins_repo: Path) -> dict:
    return parse_registry((plugins_repo / "registry.json").read_bytes())


@pytest.fixture(scope="module")
def local_fetcher(plugins_repo: Path):
    def fetch(url: str, max_bytes: int) -> bytes:
        if url == OFFICIAL_REGISTRY_URL:
            payload = (plugins_repo / "registry.json").read_bytes()
        elif url.startswith(OFFICIAL_RAW_BASE):
            payload = (plugins_repo / url[len(OFFICIAL_RAW_BASE):]).read_bytes()
        else:
            raise OSError(f"unexpected URL outside the official raw base: {url}")
        if len(payload) > max_bytes:
            raise OSError("response exceeds size limit")
        return payload

    return fetch


def _cluster_entries(registry: dict) -> list[dict]:
    seen: dict[str, dict] = {}
    for entry in registry["plugins"]:
        if entry.get("type") != "cluster-profile":
            continue
        # Latest resolvable version per id on the contract app line.
        resolved = find_registry_entry(
            registry, entry["id"], app_version=CONTRACT_APP_VERSION
        )
        seen[entry["id"]] = resolved
    return [seen[key] for key in sorted(seen)]


@pytest.mark.contract
def test_published_cluster_provider_set_is_pinned(registry: dict):
    """CON-W09-004: no published cluster provider escapes install/load proof."""
    assert hpc_gui.__version__ == CONTRACT_APP_VERSION
    assert PLUGIN_API_VERSION == 1
    actual = sorted(
        {entry["id"] for entry in registry["plugins"] if entry.get("type") == "cluster-profile"}
    )
    assert actual == sorted(EXPECTED_CLUSTER_PROVIDERS), (
        f"registry cluster-provider set changed: {actual}"
    )


@pytest.mark.integration
def test_every_published_cluster_provider_installs_and_loads(
    registry: dict, local_fetcher, tmp_path: Path
):
    """CON-W09-001/CON-W09-002: install then load every published provider.

    Before FIX-A this failed for the five community providers with
    InstallError("unknown key 'access' ... 'requirements'").
    """
    entries = _cluster_entries(registry)
    assert len(entries) == len(EXPECTED_CLUSTER_PROVIDERS)
    for entry in entries:
        root = tmp_path / entry["id"].replace(".", "_")
        result = install_plugin_from_registry(
            entry, root=root, app_version=CONTRACT_APP_VERSION, fetcher=local_fetcher
        )
        assert result.activated, entry["id"]
        loaded = load_installed_plugins(root=root, app_version=CONTRACT_APP_VERSION)
        assert loaded.problems == [], (
            f"{entry['id']}: {[p.reason for p in loaded.problems]}"
        )
        profiles = [
            p for p in loaded.plugins if p.manifest.id == entry["id"]
        ]
        assert len(profiles) == 1, entry["id"]
        profile = profiles[0].cluster_profiles[0]
        assert profile.scheduler == "slurm", entry["id"]
        assert profile.profile_id, entry["id"]


@pytest.mark.contract
def test_every_published_provider_has_explicit_capability_matrix(
    registry: dict, plugins_repo: Path
):
    """CON-W09-003: capability declaration is explicit per provider.

    The UI must never guess: storage/quota/auth/project/account each map to
    DECLARED or NOT_DECLARED straight from the shipped payload.
    """
    for entry in _cluster_entries(registry):
        manifest = json.loads(
            (plugins_repo / entry["manifest_path"]).read_text(encoding="utf-8")
        )
        for file_entry in manifest.get("files", []):
            if file_entry.get("role") != "cluster-profile":
                continue
            profile_path = (
                plugins_repo / Path(entry["manifest_path"]).parent / file_entry["path"]
            )
            raw = json.loads(profile_path.read_text(encoding="utf-8"))
            assert validate_cluster_profile_dict(raw) == [], entry["id"]
            declared = {
                item.id: item.declared
                for item in build_provider_capability_view(raw).capabilities
            }
            assert declared["scheduler"] == DECLARED, entry["id"]
            # Honesty both ways: presence declares, absence stays undeclared.
            assert declared["storage"] == (
                DECLARED if raw.get("storage") else NOT_DECLARED
            ), entry["id"]
            assert declared["quota"] == (
                DECLARED if raw.get("quota_sources") else NOT_DECLARED
            ), entry["id"]
            assert declared["project"] == (
                DECLARED if (raw.get("requirements") or {}).get("project") else NOT_DECLARED
            ), entry["id"]


@pytest.mark.contract
def test_malformed_access_or_requirements_stay_rejected():
    """NEG-W09-001: the widened allow-list does not accept wrong shapes."""
    base = {
        "schema_version": 2,
        "profile_id": "example",
        "name": "Example",
        "scheduler": "slurm",
    }
    assert validate_cluster_profile_dict({**base, "access": "lounge"}) != []
    assert validate_cluster_profile_dict({**base, "requirements": [1, 2]}) != []
    assert validate_cluster_profile_dict({**base, "access": {}, "requirements": {}}) == []


@pytest.mark.contract
def test_unknown_top_level_keys_stay_rejected():
    """NEG-W09-002: fail-closed unknown-key behavior is unchanged."""
    profile = {
        "schema_version": 2,
        "profile_id": "example",
        "name": "Example",
        "scheduler": "slurm",
        "frobnicate": True,
    }
    errors = validate_cluster_profile_dict(profile)
    assert any("frobnicate" in error for error in errors)


@pytest.mark.integration
def test_rejected_install_leaves_no_active_or_half_loaded_plugin(
    registry: dict, local_fetcher, tmp_path: Path
):
    """NEG-W09-003: installer rejection leaves nothing half-installed.

    A schema-3 payload on the 1.5.8 line must raise InstallError AND leave
    no active index entry and no loadable plugin behind.
    """
    from hpc_gui.plugins.storage import read_active_versions

    entry = find_registry_entry(
        registry,
        "org.hpcclient.truba",
        version="1.4.0",
        app_version=CONTRACT_APP_VERSION,
    )
    with pytest.raises(InstallError, match="requires app >=1.5.9"):
        install_plugin_from_registry(
            entry, root=tmp_path, app_version="1.5.8", fetcher=local_fetcher
        )
    assert read_active_versions(root=tmp_path) == {}
    loaded = load_installed_plugins(root=tmp_path, app_version="1.5.8")
    assert loaded.plugins == []
    assert loaded.problems == []

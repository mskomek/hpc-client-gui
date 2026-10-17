from __future__ import annotations

import hashlib
import json
from pathlib import Path
import pytest
from hpc_gui.plugins.downloader import (
    DownloadError,
    compute_local_sha256,
    download_exact_file,
    payload_url,
    validate_payload_rel_path,
)
from hpc_gui.plugins.installer import STAGING_DIR_NAME, InstallError, install_plugin_from_registry
from hpc_gui.plugins.loader import load_installed_plugins
from hpc_gui.plugins.registry_client import (
    FILE_MAX_BYTES,
    MANIFEST_MAX_BYTES,
    OFFICIAL_RAW_BASE,
    OFFICIAL_REGISTRY_URL,
    REGISTRY_MAX_BYTES,
    RegistryError,
    fetch_registry_with_cache,
    find_registry_entry,
    parse_registry,
)
from hpc_gui.plugins.state import read_installed_state
from hpc_gui.plugins.storage import packages_dir, plugins_root, read_active_versions
VALID_REGISTRY = {
    "schema_version": 1,
    "plugin_api": 1,
    "repository": {
        "owner": "mskomek",
        "name": "hpc-client-gui-plugins",
        "raw_base": OFFICIAL_RAW_BASE,
    },
    "plugins": [],
}
def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
def make_plugin_files(
    *,
    plugin_id: str = "org.hpcclient.truba",
    version: str = "1.0.0",
    requires_app: str = ">=1.3.0",
    schema_version: int = 1,
) -> tuple[dict, bytes, bytes]:
    """Build a self-consistent manifest + cluster profile pair."""
    profile = {
        "schema_version": schema_version,
        "profile_id": "truba",
        "name": "TRUBA",
        "scheduler": "slurm",
        "paths": {"home_dir": "/arf/home/{user}", "scratch_dir": "/arf/scratch/{user}"},
        "commands": {"status_command": "lssrv"},
    }
    if schema_version >= 3:
        profile["job_outputs"] = {
            "strategy": "explicit",
            "streams": [
                {
                    "id": "stdout",
                    "role": "stdout",
                    "labels": {"en": "Standard Output"},
                    "resolver": "slurm.stdout",
                    "order": 10,
                }
            ],
        }
    profile_bytes = json.dumps(profile).encode("utf-8")
    manifest = {
        "schema_version": 1,
        "plugin_api": 1,
        "id": plugin_id,
        "name": "TRUBA",
        "version": version,
        "publisher": "HPC Client GUI",
        "license": "MIT",
        "description": "TRUBA cluster profile.",
        "requires_app": requires_app,
        "capabilities": ["cluster-profile"],
        "entrypoints": {"cluster_profiles": ["cluster-profile.json"]},
        "files": [
            {
                "path": "cluster-profile.json",
                "sha256": sha256_bytes(profile_bytes),
                "size": len(profile_bytes),
                "role": "cluster-profile",
            }
        ],
    }
    manifest_bytes = json.dumps(manifest).encode("utf-8")
    return manifest, manifest_bytes, profile_bytes
def make_registry_entry(manifest: dict, manifest_bytes: bytes) -> dict:
    return {
        "id": manifest["id"],
        "name": manifest["name"],
        "version": manifest["version"],
        "plugin_api": 1,
        "type": "cluster-profile",
        "description": manifest["description"],
        "publisher": manifest["publisher"],
        "requires_app": manifest["requires_app"],
        "manifest_path": f"plugins/{manifest['id'].split('.')[-1]}/{manifest['version']}/manifest.json",
        "manifest_sha256": sha256_bytes(manifest_bytes),
        "official": True,
    }
def make_fetcher(responses: dict[str, bytes]):
    def fetch(url: str, max_bytes: int) -> bytes:
        if url not in responses:
            raise OSError(f"no response registered for {url}")
        payload = responses[url]
        if len(payload) > max_bytes:
            raise OSError(f"response exceeds {max_bytes} bytes")
        return payload

    return fetch
def make_fluent_entry(version: str, requires_app: str = ">=1.4.0") -> dict:
    return {
        "id": "org.hpcclient.fluent",
        "name": "Fluent Tools",
        "version": version,
        "plugin_api": 1,
        "type": "lint-rules",
        "description": "Fluent tools.",
        "publisher": "HPC Client GUI",
        "requires_app": requires_app,
        "manifest_path": f"plugins/fluent/{version}/manifest.json",
        "manifest_sha256": sha256_bytes(version.encode()),
        "official": True,
    }
def fluent_registry(*entries) -> dict:
    return {**VALID_REGISTRY, "plugins": list(entries)}
def full_install_responses(**overrides) -> dict[str, bytes]:
    manifest, manifest_bytes, profile_bytes = make_plugin_files(**overrides)
    base = f"plugins/{manifest['id'].split('.')[-1]}/{manifest['version']}"
    return {
        OFFICIAL_RAW_BASE + base + "/manifest.json": manifest_bytes,
        OFFICIAL_RAW_BASE + base + "/cluster-profile.json": profile_bytes,
    }, manifest, manifest_bytes
def _assert_no_staging_or_part_leftovers(tmp_path: Path) -> None:
    base = Path(plugins_root(tmp_path))
    staging = base / STAGING_DIR_NAME
    assert not staging.exists() or not any(staging.iterdir())
    assert not list(base.rglob("*.part"))
    assert not list(base.rglob("*.tmp"))

__all__ = [
    'hashlib',
    'json',
    'Path',
    'pytest',
    'DownloadError',
    'compute_local_sha256',
    'download_exact_file',
    'payload_url',
    'validate_payload_rel_path',
    'STAGING_DIR_NAME',
    'InstallError',
    'install_plugin_from_registry',
    'load_installed_plugins',
    'FILE_MAX_BYTES',
    'MANIFEST_MAX_BYTES',
    'OFFICIAL_RAW_BASE',
    'OFFICIAL_REGISTRY_URL',
    'REGISTRY_MAX_BYTES',
    'RegistryError',
    'fetch_registry_with_cache',
    'find_registry_entry',
    'parse_registry',
    'read_installed_state',
    'packages_dir',
    'plugins_root',
    'read_active_versions',
    'VALID_REGISTRY',
    'sha256_bytes',
    'make_plugin_files',
    'make_registry_entry',
    'make_fetcher',
    'make_fluent_entry',
    'fluent_registry',
    'full_install_responses',
    '_assert_no_staging_or_part_leftovers',
]

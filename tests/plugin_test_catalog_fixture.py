"""Shared builder for local test catalogs (see plugins/test_catalog.py)."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest

from hpc_gui.plugins.registry_client import OFFICIAL_RAW_BASE
from hpc_gui.plugins.test_catalog import TEST_CATALOG_ENV, TEST_MODE_ENV

PLUGIN_ID = "org.hpcclient.testcatalog"
SLUG = "test-catalog-plugin"
DEFAULT_FILES = {"data/readme.json": b'{"revision": 1}\n'}


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def manifest_bytes(version: str, files: dict[str, bytes]) -> bytes:
    manifest = {
        "schema_version": 1,
        "plugin_api": 1,
        "id": PLUGIN_ID,
        "name": "Test Catalog Plugin",
        "version": version,
        "publisher": "HPC Client QA",
        "license": "MIT",
        "description": "Local test catalog fixture.",
        "requires_app": ">=1.0.0",
        "capabilities": ["application-tools"],
        "entrypoints": {},
        "files": [
            {"path": rel, "sha256": sha256_hex(data), "size": len(data), "role": "documentation"}
            for rel, data in files.items()
        ],
    }
    return (json.dumps(manifest, indent=2) + "\n").encode("utf-8")


def write_catalog(root: Path, versions: dict[str, dict[str, bytes]], *, raw_base: str = OFFICIAL_RAW_BASE) -> dict:
    """Write registry.json plus per-version manifests and payloads under ``root``."""
    entries = []
    for version, files in versions.items():
        base = f"plugins/{SLUG}/{version}"
        manifest = manifest_bytes(version, files)
        version_dir = root / base
        version_dir.mkdir(parents=True, exist_ok=True)
        (version_dir / "manifest.json").write_bytes(manifest)
        for rel, data in files.items():
            (version_dir / rel).parent.mkdir(parents=True, exist_ok=True)
            (version_dir / rel).write_bytes(data)
        entries.append(
            {
                "id": PLUGIN_ID,
                "name": "Test Catalog Plugin",
                "version": version,
                "plugin_api": 1,
                "type": "application-tools",
                "description": "Local test catalog fixture.",
                "publisher": "HPC Client QA",
                "requires_app": ">=1.0.0",
                "manifest_path": f"{base}/manifest.json",
                "manifest_sha256": sha256_hex(manifest),
                "official": False,
            }
        )
    registry = {
        "schema_version": 1,
        "plugin_api": 1,
        "repository": {"owner": "mskomek", "name": "hpc-client-gui-plugins", "raw_base": raw_base},
        "plugins": entries,
    }
    (root / "registry.json").write_text(json.dumps(registry, indent=2), encoding="utf-8")
    return registry


def enable_test_catalog(monkeypatch, root: Path) -> None:
    monkeypatch.setenv(TEST_MODE_ENV, "1")
    monkeypatch.setenv(TEST_CATALOG_ENV, root.as_uri())


def make_dir_link(link: Path, target: Path) -> None:
    """Create a directory symlink, or a Windows junction, or skip the test."""
    try:
        os.symlink(target, link, target_is_directory=True)
        return
    except OSError:
        pass
    if os.name == "nt":
        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(target)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return
    pytest.skip("directory symlink or junction cannot be created on this host")

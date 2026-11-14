"""Shared fixtures for the W33 plugin lifecycle isolation suite.

Split out of test_w33_lifecycle_isolation.py so each file keeps a cohesive
responsibility and stays under the source-size gate.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from hpc_gui.plugins.models import PLUGIN_API_VERSION


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

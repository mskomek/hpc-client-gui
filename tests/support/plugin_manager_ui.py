"""Shared fixtures and static registry payload for plugin-manager UI tests."""

from __future__ import annotations

import hashlib
import json

from hpc_gui.plugins.registry_client import (
    OFFICIAL_RAW_BASE,
    OFFICIAL_REGISTRY_URL,
    RegistryFetchResult,
)
from hpc_gui.ui.dialogs.plugin_manager_dialog import PluginManagerDialog

VALID_REGISTRY = {
    "schema_version": 1,
    "plugin_api": 1,
    "repository": {
        "owner": "mskomek",
        "name": "hpc-client-gui-plugins",
        "raw_base": OFFICIAL_RAW_BASE,
    },
    "plugins": [
        {
            "id": "org.hpcclient.truba",
            "name": "TRUBA",
            "version": "1.0.0",
            "plugin_api": 1,
            "type": "cluster-profile",
            "description": "TRUBA system profile for HPC Client GUI.",
            "publisher": "HPC Client GUI",
            "requires_app": ">=1.3.0",
            "manifest_path": "plugins/truba/1.0.0/manifest.json",
            "manifest_sha256": hashlib.sha256(b"manifest").hexdigest(),
            "official": True,
        },
        {
            "id": "org.hpcclient.future",
            "name": "Future Plugin",
            "version": "9.9.9",
            "plugin_api": 1,
            "type": "lint-rules",
            "description": "Requires a much newer app.",
            "publisher": "HPC Client GUI",
            "requires_app": ">=99.0.0",
            "manifest_path": "plugins/future/9.9.9/manifest.json",
            "manifest_sha256": hashlib.sha256(b"m2").hexdigest(),
            "official": True,
        },
    ],
}

def registry_fetcher():
    payload = json.dumps(VALID_REGISTRY).encode()

    def fetch(url: str, max_bytes: int) -> bytes:
        assert url == OFFICIAL_REGISTRY_URL
        return payload

    return fetch


def apply_registry(dialog: PluginManagerDialog, source: str = "network") -> None:
    """Drive the async refresh completion handler synchronously."""
    dialog._on_registry_loaded(json.loads(json.dumps(VALID_REGISTRY)), source)


def _registry_fetch_result(source: str = "network") -> RegistryFetchResult:
    return RegistryFetchResult(
        registry=json.loads(json.dumps(VALID_REGISTRY)),
        source=source,
        fetched_at="now",
    )

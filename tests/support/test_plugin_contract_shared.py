from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path
import pytest
from hpc_gui.plugins.compatibility import (
    effective_requires_app,
    is_app_compatible,
    validate_compatibility_override,
)
from hpc_gui.plugins.installer import InstallError, install_plugin_from_registry
from hpc_gui.plugins.loader import load_installed_plugins
from hpc_gui.plugins.registry_client import (
    OFFICIAL_RAW_BASE,
    OFFICIAL_REGISTRY_URL,
    find_registry_entry,
    parse_registry,
)
from hpc_gui.plugins.schema_compat import (
    MIN_APP_VERSION_FOR_SCHEMA,
    app_supports_schema,
    schema_floor_error,
)
from hpc_gui.plugins.state import activate_version
from hpc_gui.plugins.validator import validate_registry_dict
CONTRACT_APP_VERSION = "1.5.9"
RELEASED_APP_VERSION = "1.5.8"
OLDEST_SUPPORTED_APP_VERSION = "1.5.5"
REPO = os.environ.get("HPC_GUI_CONTRACT_REPO", "")
@pytest.fixture(scope="module")
def plugins_repo() -> Path:
    return Path(REPO).resolve()
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
@pytest.fixture(scope="module")
def registry(plugins_repo: Path) -> dict:
    return parse_registry((plugins_repo / "registry.json").read_bytes())
def _install(local_fetcher, tmp_path: Path, entry: dict, app_version: str = CONTRACT_APP_VERSION):
    return install_plugin_from_registry(
        entry,
        root=tmp_path,
        app_version=app_version,
        fetcher=local_fetcher,
    )

__all__ = [
    'importlib',
    'json',
    'os',
    'sys',
    'Path',
    'pytest',
    'effective_requires_app',
    'is_app_compatible',
    'validate_compatibility_override',
    'InstallError',
    'install_plugin_from_registry',
    'load_installed_plugins',
    'OFFICIAL_RAW_BASE',
    'OFFICIAL_REGISTRY_URL',
    'find_registry_entry',
    'parse_registry',
    'MIN_APP_VERSION_FOR_SCHEMA',
    'app_supports_schema',
    'schema_floor_error',
    'activate_version',
    'validate_registry_dict',
    'CONTRACT_APP_VERSION',
    'RELEASED_APP_VERSION',
    'OLDEST_SUPPORTED_APP_VERSION',
    'REPO',
    'plugins_repo',
    'local_fetcher',
    'registry',
    '_install',
]

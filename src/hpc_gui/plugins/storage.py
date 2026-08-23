"""Local plugin storage locations and index files.

All paths flow through these helpers so tests can override the root; no UI
or service module may hardcode plugin paths.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping

from hpc_gui.core.paths import app_data_dir
from hpc_gui.plugins.models import PLUGIN_API_VERSION

INSTALLED_INDEX_NAME = "installed.json"
ACTIVE_INDEX_NAME = "active.json"
PACKAGES_DIR_NAME = "packages"
MANIFEST_NAME = "manifest.json"
DISABLED_FILE_NAME = "disabled.json"


def read_disabled_ids(root: str | Path | None = None) -> set[str]:
    """Read the disabled-plugin id set; disabled plugins stay installed but
    contribute no templates or rules."""
    value = _read_json_object(plugins_root(root) / DISABLED_FILE_NAME)
    raw = value.get("disabled")
    if not isinstance(raw, list):
        return set()
    return {str(item) for item in raw if isinstance(item, str) and item}


def write_disabled_ids(disabled, root: str | Path | None = None) -> None:
    base = plugins_root(root)
    base.mkdir(parents=True, exist_ok=True)
    payload = {"disabled": sorted(set(disabled))}
    temporary = base / (DISABLED_FILE_NAME + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
    temporary.replace(base / DISABLED_FILE_NAME)


def plugins_root(override: str | Path | None = None) -> Path:
    """Return the plugins data root (``<app data>/plugins``).

    ``override`` exists for tests and explicit user configuration only.
    """
    if override is not None:
        return Path(override)
    return app_data_dir() / "plugins"


def packages_dir(root: str | Path | None = None) -> Path:
    return plugins_root(root) / PACKAGES_DIR_NAME


def plugin_package_dir(plugin_id: str, version: str, root: str | Path | None = None) -> Path:
    return packages_dir(root) / plugin_id / version


def manifest_path(plugin_id: str, version: str, root: str | Path | None = None) -> Path:
    return plugin_package_dir(plugin_id, version, root) / MANIFEST_NAME


def _read_json_object(path: Path) -> Mapping[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
    except FileNotFoundError:
        return {}
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def read_installed_index(root: str | Path | None = None) -> dict[str, Any]:
    """Read the installed-plugin index (plugin id -> install metadata)."""
    value = _read_json_object(plugins_root(root) / INSTALLED_INDEX_NAME)
    return {str(key): item for key, item in value.items()}


def write_installed_index(index: Mapping[str, Any], root: str | Path | None = None) -> None:
    base = plugins_root(root)
    base.mkdir(parents=True, exist_ok=True)
    with (base / INSTALLED_INDEX_NAME).open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(dict(index), handle, indent=2, sort_keys=True)
        handle.write("\n")


def read_active_versions(root: str | Path | None = None) -> dict[str, str]:
    """Read active.json.

    Canonical layout is ``{"plugin_api": 1, "active": {id: version}}``;
    a legacy flat ``{id: version}`` mapping is also accepted.
    """
    value = _read_json_object(plugins_root(root) / ACTIVE_INDEX_NAME)
    inner = value.get("active")
    source = inner if isinstance(inner, dict) else value
    result: dict[str, str] = {}
    for key, version in source.items():
        if key == "plugin_api":
            continue
        if isinstance(version, str) and version:
            result[str(key)] = version
    return result


def write_active_versions(active: Mapping[str, str], root: str | Path | None = None) -> None:
    base = plugins_root(root)
    base.mkdir(parents=True, exist_ok=True)
    payload = {
        "plugin_api": PLUGIN_API_VERSION,
        "active": dict(active),
    }
    # Atomic replace so a crash can never leave a truncated or half-written
    # active-version pointer behind.
    target = base / ACTIVE_INDEX_NAME
    temporary = base / (ACTIVE_INDEX_NAME + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(target)

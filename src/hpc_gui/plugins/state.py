"""Installed-plugin bookkeeping (installed.json + activation)."""

from __future__ import annotations

import json
import logging
import os
import shutil
import time
from collections.abc import Callable
from pathlib import Path
from typing import Mapping

from hpc_gui.plugins.storage import (
    packages_dir,
    plugins_root,
    read_active_versions,
    read_disabled_ids,
    write_active_versions,
    write_disabled_ids,
)

logger = logging.getLogger(__name__)

INSTALLED_SCHEMA_VERSION = 2


def _atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def installed_index_path(root: str | Path | None = None) -> Path:
    return plugins_root(root) / "installed.json"


def read_installed_state(root: str | Path | None = None) -> dict[str, dict]:
    """Read the installed index; returns ``{plugin_id: {versions, ...}}``."""
    try:
        with installed_index_path(root).open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict) or not isinstance(payload.get("plugins"), dict):
        return {}
    result: dict[str, dict] = {}
    for plugin_id, record in payload["plugins"].items():
        if isinstance(record, dict) and isinstance(record.get("versions"), list):
            hashes = record.get("manifest_hashes")
            migrated = record.get("migrated")
            result[str(plugin_id)] = {
                "versions": [str(v) for v in record["versions"] if isinstance(v, str)],
                "installed_at": str(record.get("installed_at", "")),
                "manifest_hashes": (
                    {str(k): str(v) for k, v in hashes.items() if isinstance(v, str)}
                    if isinstance(hashes, dict)
                    else {}
                ),
                "migrated": (
                    [str(v) for v in migrated if isinstance(v, str)]
                    if isinstance(migrated, list)
                    else []
                ),
            }
    return result


def write_installed_state(state: Mapping[str, dict], root: str | Path | None = None) -> None:
    _atomic_write_json(
        installed_index_path(root),
        {"schema_version": INSTALLED_SCHEMA_VERSION, "plugins": dict(state)},
    )


def record_installed_version(
    plugin_id: str,
    version: str,
    *,
    root: str | Path | None = None,
    activate: bool = True,
    now: Callable[[], str] | None = None,
    manifest_sha256: str | None = None,
) -> None:
    """Record an installed version in installed.json (and activate it).

    Activation happens only after the caller has fully verified the install;
    failures before this point must leave previous state untouched. The
    verified manifest SHA-256 is stored as the version's trust anchor for
    later local integrity re-validation.
    """
    timestamp = (
        now or (lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    )()
    state = read_installed_state(root)
    record = state.setdefault(plugin_id, {"versions": [], "installed_at": timestamp})
    versions = [v for v in record.get("versions", []) if v != version]
    versions.append(version)
    record["versions"] = sorted(versions, key=_version_sort_key)
    record.setdefault("installed_at", timestamp)
    if manifest_sha256:
        hashes = record.setdefault("manifest_hashes", {})
        if isinstance(hashes, dict):
            hashes[version] = manifest_sha256
        migrated = record.get("migrated")
        if isinstance(migrated, list) and version in migrated:
            migrated.remove(version)
    # Keep insertion order stable for readability.
    write_installed_state(state, root=root)
    if activate:
        active = read_active_versions(root)
        active[plugin_id] = version
        write_active_versions(active, root=root)


def _version_sort_key(value: str):
    from packaging.version import InvalidVersion, Version

    try:
        return (0, Version(str(value)))
    except InvalidVersion:
        return (1, Version("0"))


def remove_plugin(plugin_id: str, root: str | Path | None = None) -> list[str]:
    """Remove every installed version of a plugin and deactivate it.

    Only plugin-owned files under ``<plugins>/packages/<plugin_id>`` are
    deleted. Saved connection profiles and user templates are never touched.
    Returns the versions that were removed.
    """
    state = read_installed_state(root)
    record = state.pop(plugin_id, {})
    removed = list(record.get("versions", []))
    write_installed_state(state, root=root)

    active = read_active_versions(root)
    if plugin_id in active:
        del active[plugin_id]
        write_active_versions(active, root=root)

    package_dir = packages_dir(root) / plugin_id
    if package_dir.exists():
        shutil.rmtree(package_dir, ignore_errors=True)
    logger.info("Removed plugin %s (versions: %s)", plugin_id, ", ".join(removed) or "none")
    return removed


def activate_version(plugin_id: str, version: str, root: str | Path | None = None) -> None:
    """Activate an installed plugin version after validating it.

    Only versions that are present on disk and load cleanly may become
    active; the previous active pointer is restored if validation fails.
    """
    from hpc_gui.plugins.loader import load_installed_plugins

    previous = read_active_versions(root).get(plugin_id)

    def _set(pointer_version: str | None) -> None:
        active = read_active_versions(root)
        if pointer_version is None:
            active.pop(plugin_id, None)
        else:
            active[plugin_id] = pointer_version
        write_active_versions(active, root=root)

    _set(version)
    loaded = load_installed_plugins(root=root)
    ok = any(
        installed.manifest.id == plugin_id and installed.manifest.version == version
        for installed in loaded.plugins
    )
    if not ok:
        logger.warning(
            "Activation of %s@%s failed validation; restoring %s",
            plugin_id,
            version,
            previous or "<inactive>",
        )
        _set(previous)
        raise ValueError(f"Plugin {plugin_id}@{version} failed validation and was not activated.")
    logger.info("Activated plugin %s@%s", plugin_id, version)


def set_plugin_disabled(plugin_id: str, disabled: bool, root: str | Path | None = None) -> None:
    """Disable/enable a plugin without deleting any files.

    A disabled plugin contributes no templates or rules; saved profiles are
    unaffected because they embed resolved snapshots.
    """
    current = read_disabled_ids(root)
    if disabled:
        current.add(plugin_id)
    else:
        current.discard(plugin_id)
    write_disabled_ids(current, root=root)
    logger.info("Plugin %s %s", plugin_id, "disabled" if disabled else "enabled")

"""Installed-plugin bookkeeping (installed.json + activation)."""

from __future__ import annotations

import logging
import shutil
import time
from collections.abc import Callable
from pathlib import Path

from hpc_gui.plugins.storage import (
    packages_dir,
    plugins_root,  # noqa: F401 — legacy re-export
    read_active_versions,
    read_disabled_ids,
    write_active_versions,
    write_disabled_ids,
)
from hpc_gui.plugins.installed_state import (
    INSTALLED_SCHEMA_VERSION,  # noqa: F401 — legacy re-export
    installed_index_path,  # noqa: F401 — legacy re-export
    read_installed_state,
    write_installed_state,
)

logger = logging.getLogger(__name__)

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

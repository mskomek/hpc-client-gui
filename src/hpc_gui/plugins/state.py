"""Installed-plugin bookkeeping (installed.json + activation)."""

from __future__ import annotations

import json
import os
import time
from collections.abc import Callable
from pathlib import Path
from typing import Mapping

from hpc_gui.plugins.storage import (
    plugins_root,
    read_active_versions,
    write_active_versions,
)

INSTALLED_SCHEMA_VERSION = 1


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
            result[str(plugin_id)] = {
                "versions": [str(v) for v in record["versions"] if isinstance(v, str)],
                "installed_at": str(record.get("installed_at", "")),
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
) -> None:
    """Record an installed version in installed.json (and activate it).

    Activation happens only after the caller has fully verified the install;
    failures before this point must leave previous state untouched.
    """
    timestamp = (
        now or (lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    )()
    state = read_installed_state(root)
    record = state.setdefault(plugin_id, {"versions": [], "installed_at": timestamp})
    versions = [v for v in record.get("versions", []) if v != version]
    versions.append(version)
    record["versions"] = sorted(versions)
    record.setdefault("installed_at", timestamp)
    # Keep insertion order stable for readability.
    write_installed_state(state, root=root)
    if activate:
        active = read_active_versions(root)
        active[plugin_id] = version
        write_active_versions(active, root=root)

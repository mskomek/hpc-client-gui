"""Durable installed-version index shared by plugin lifecycle modules."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from pathlib import Path

from hpc_gui.plugins.storage import plugins_root

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
    if os.name == "posix":
        path.chmod(0o600)


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
                "versions": [str(value) for value in record["versions"] if isinstance(value, str)],
                "installed_at": str(record.get("installed_at", "")),
                "manifest_hashes": (
                    {str(key): str(value) for key, value in hashes.items() if isinstance(value, str)}
                    if isinstance(hashes, dict)
                    else {}
                ),
                "migrated": (
                    [str(value) for value in migrated if isinstance(value, str)]
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

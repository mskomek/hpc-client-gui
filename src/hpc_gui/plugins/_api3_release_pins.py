"""Strict parser for application-owned Plugin API v3 release-pin data."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Callable, Mapping


@dataclass(frozen=True, slots=True)
class Api3Pin:
    """Immutable host-approved contract for one exact plugin release."""

    plugin_id: str
    version: str
    publisher: str = "HPC Client GUI"
    api: int = 3
    capabilities: tuple[str, ...] = ()
    entrypoints: tuple[tuple[str, str], ...] = ()
    files: tuple[tuple[str, str, str], ...] = ()
    manifest_sha256: str | None = None


def _unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate release-pin key: {key}")
        value[key] = item
    return value


def load_application_release_pins(
    path: Path,
    *,
    expected: Mapping[
        tuple[str, str], tuple[tuple[str, ...], tuple[tuple[str, str], ...], str]
    ],
    publisher: str,
    api: int,
    validate_path_role: Callable[[str, str], str | None],
) -> Mapping[tuple[str, str], Api3Pin]:
    """Load complete, exact host policy; malformed input returns an empty map."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
        if not isinstance(raw, dict) or set(raw) != {"schema_version", "source_commit", "pins"}:
            return MappingProxyType({})
        if raw["schema_version"] != 1 or not isinstance(raw["source_commit"], str):
            return MappingProxyType({})
        if not re.fullmatch(r"[0-9a-f]{40}", raw["source_commit"]):
            return MappingProxyType({})
        entries = raw["pins"]
        if not isinstance(entries, list):
            return MappingProxyType({})
        result: dict[tuple[str, str], Api3Pin] = {}
        fields = {
            "plugin_id", "version", "publisher", "api", "capabilities",
            "entrypoints", "files", "manifest_sha256",
        }
        for entry in entries:
            if not isinstance(entry, dict) or set(entry) != fields:
                return MappingProxyType({})
            key = (entry["plugin_id"], entry["version"])
            contract = expected.get(key)
            if contract is None or key in result:
                return MappingProxyType({})
            capabilities, entrypoints, executable_role = contract
            if not isinstance(entry["capabilities"], list):
                return MappingProxyType({})
            if not isinstance(entry["entrypoints"], dict) or not isinstance(entry["files"], list):
                return MappingProxyType({})
            digest = entry["manifest_sha256"]
            if (
                entry["publisher"] != publisher
                or entry["api"] != api
                or tuple(entry["capabilities"]) != capabilities
                or tuple(sorted(entry["entrypoints"].items())) != tuple(sorted(entrypoints))
                or not isinstance(digest, str)
                or not re.fullmatch(r"[0-9a-f]{64}", digest)
            ):
                return MappingProxyType({})
            files: list[tuple[str, str, str]] = []
            seen: set[str] = set()
            for row in entry["files"]:
                if (
                    not isinstance(row, list)
                    or len(row) != 3
                    or not all(isinstance(item, str) for item in row)
                    or row[0] in seen
                    or validate_path_role(row[0], row[1]) is not None
                    or not re.fullmatch(r"[0-9a-f]{64}", row[2])
                ):
                    return MappingProxyType({})
                seen.add(row[0])
                files.append((row[0], row[1], row[2]))
            key_name = "linter_engine" if executable_role == "linter-engine" else "application_tool"
            executable_path = dict(entrypoints).get(key_name)
            if not files or executable_path not in {
                name for name, role, _sha in files if role == executable_role
            }:
                return MappingProxyType({})
            result[key] = Api3Pin(
                key[0], key[1], publisher=publisher, api=api,
                capabilities=capabilities, entrypoints=entrypoints,
                files=tuple(files), manifest_sha256=digest,
            )
        if set(result) != set(expected):
            return MappingProxyType({})
        return MappingProxyType(result)
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError, KeyError):
        return MappingProxyType({})

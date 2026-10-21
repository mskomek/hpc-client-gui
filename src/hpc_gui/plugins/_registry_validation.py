from __future__ import annotations

from typing import Any

from hpc_gui.plugins._validator_contracts import DISCOVERABLE_PLUGIN_API_VERSIONS, REGISTRY_ENTRY_REQUIRED_KEYS, REGISTRY_PLUGIN_TYPES, _is_sha256_hex
from hpc_gui.plugins.compatibility import validate_compatibility_override, validate_requires_app
from hpc_gui.plugins.models import (
    PLUGIN_API_VERSION,
    is_safe_relative_path, is_valid_semver,
)

def validate_registry_dict(registry: Any) -> list[str]:
    """Validate a raw registry mapping; returns human-readable problems."""
    if not isinstance(registry, dict):
        return ["registry must be a JSON object"]
    errors: list[str] = []
    if registry.get("schema_version") != 1:
        errors.append("registry schema_version must be 1")
    if registry.get("plugin_api") != PLUGIN_API_VERSION:
        errors.append(f"registry plugin_api must be {PLUGIN_API_VERSION}")

    repository = registry.get("repository")
    if not isinstance(repository, dict):
        errors.append("registry repository must be a JSON object")
    else:
        raw_base = repository.get("raw_base")
        if (
            not isinstance(raw_base, str)
            or not raw_base.startswith("https://")
            or not raw_base.endswith("/")
        ):
            errors.append("registry repository.raw_base must be an HTTPS URL ending with '/'")

    plugins = registry.get("plugins")
    if not isinstance(plugins, list):
        errors.append("registry plugins must be a list")
        return errors

    seen: set[tuple[str, str]] = set()
    for entry in plugins:
        if not isinstance(entry, dict):
            errors.append("each registry plugin entry must be a JSON object")
            continue
        plugin_id = entry.get("id", "<missing>")
        label = f"registry entry {plugin_id}"
        for key in REGISTRY_ENTRY_REQUIRED_KEYS:
            if key not in entry:
                errors.append(f"{label} is missing required key '{key}'")
        if any(key not in entry for key in REGISTRY_ENTRY_REQUIRED_KEYS):
            continue
        if not is_valid_semver(entry["version"]):
            errors.append(f"{label}: invalid semantic version {entry['version']!r}")
        if entry["plugin_api"] not in DISCOVERABLE_PLUGIN_API_VERSIONS:
            supported = ", ".join(str(v) for v in sorted(DISCOVERABLE_PLUGIN_API_VERSIONS))
            errors.append(
                f"{label}: unsupported plugin_api {entry['plugin_api']!r} (supported: {supported})"
            )
        if entry["type"] not in REGISTRY_PLUGIN_TYPES:
            errors.append(f"{label}: unknown plugin type {entry['type']!r}")
        if not is_safe_relative_path(entry["manifest_path"]):
            errors.append(f"{label}: unsafe manifest_path {entry['manifest_path']!r}")
        if not _is_sha256_hex(entry["manifest_sha256"]):
            errors.append(f"{label}: manifest_sha256 must be 64 lowercase hex chars")
        if not isinstance(entry["official"], bool):
            errors.append(f"{label}: 'official' must be a boolean")
        errors.extend(
            f"{label}: {problem}" for problem in validate_requires_app(entry["requires_app"])
        )
        # Registry-level compatibility correction for an immutable published
        # package. The application validates the field itself: the registry
        # is a separate trust boundary, and an override that widens
        # compatibility would advertise an install the app must refuse.
        errors.extend(
            f"{label}: {problem}" for problem in validate_compatibility_override(entry)
        )
        identity = (str(entry["id"]), str(entry["version"]))
        if identity in seen:
            errors.append(f"{label}: duplicate (id, version) pair in registry")
        seen.add(identity)
    return errors

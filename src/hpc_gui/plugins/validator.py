"""Structural validation for declarative plugin payloads.

Pure-Python, dependency-free checks that mirror the registry-side JSON
Schemas closely enough to reject malformed or unsafe local installs.
"""

from __future__ import annotations

import re
from pathlib import PurePosixPath
from typing import Any

from hpc_gui.plugins.compatibility import validate_requires_app
from hpc_gui.plugins.trusted_tools import trusted_tool_error
from hpc_gui.plugins.models import (
    CAPABILITY_LINTER_TOOL,
    KNOWN_CAPABILITIES,
    KNOWN_FILE_ROLES,
    PLUGIN_API_VERSION,
    SUPPORTED_PLUGIN_API_VERSIONS,
    is_safe_relative_path,
    is_valid_semver,
)

MANIFEST_REQUIRED_KEYS = (
    "schema_version",
    "plugin_api",
    "id",
    "name",
    "version",
    "publisher",
    "license",
    "description",
    "requires_app",
    "capabilities",
    "entrypoints",
    "files",
)

MANIFEST_OPTIONAL_KEYS = frozenset({"ui_contributions"})

CLUSTER_PROFILE_REQUIRED_KEYS = ("schema_version", "profile_id", "name", "scheduler")
V2_PROFILE_SECTIONS = frozenset(
    {"description", "metadata", "paths", "commands", "site", "scheduler_hints", "software", "storage", "quota_sources"}
)

KNOWN_SCHEDULERS = frozenset({"slurm"})

_TRUSTED_SLURM_COMMANDS = {
    "squeue_command": 'squeue -h -u {user} -o "%i|%P|%j|%u|%T|%M|%D|%C|%R"',
    "sbatch_command": "cd -- {script_dir_q} && sbatch -- {script_name_q}",
    "scancel_command": "scancel {job_id_q}",
    "sacct_command": "sacct -u {user} --format=JobID,JobName,State,Elapsed,MaxRSS,AllocTRES",
    "scontrol_command": "scontrol show job {job_id_q}",
    "status_command": "lssrv",
    "active_job_ids_command": 'squeue -h -u {user} -o "%A"',
    "job_state_command": "sacct -n -X -j {job_id_q} -o State -P",
}

# Declarative payloads only; anything runnable is forbidden regardless of role.
ALLOWED_PAYLOAD_SUFFIXES = frozenset({".json", ".md", ".txt", ".tpl"})
V2_LINTER_ENGINE_ROLE = "linter-engine"
V2_LINTER_DATA_ROLE = "linter-data"
V2_LINTER_ENTRYPOINT_KEY = "linter_engine"
TRUSTED_DECLARATIVE_ENGINES = frozenset({"declarative-rules-v1"})

# Placeholders the scheduler backend actually interpolates. Unknown forms are
# rejected so a malformed/malicious template cannot inject format surprises.
KNOWN_COMMAND_PLACEHOLDERS = frozenset(
    {
        "user",
        "job_id",
        "job_id_q",
        "script_dir",
        "script_dir_q",
        "script_name",
        "script_name_q",
    }
)

_PLACEHOLDER_RE = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")


def _is_nonempty_str(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_manifest_dict(manifest: Any) -> list[str]:
    """Validate a raw manifest mapping; returns human-readable problems."""
    if not isinstance(manifest, dict):
        return ["manifest must be a JSON object"]
    errors: list[str] = []

    for key in MANIFEST_REQUIRED_KEYS:
        if key not in manifest:
            errors.append(f"manifest is missing required key '{key}'")
    if errors:
        return errors
    # Reject unknown top-level keys except optional ui_contributions
    allowed_keys = set(MANIFEST_REQUIRED_KEYS) | MANIFEST_OPTIONAL_KEYS
    unknown = set(manifest) - allowed_keys
    if unknown:
        errors.append(f"manifest has unknown properties {sorted(unknown)}")
        return errors

    if manifest["schema_version"] != 1:
        errors.append("manifest schema_version must be 1")
    if manifest["plugin_api"] not in SUPPORTED_PLUGIN_API_VERSIONS:
        supported = ", ".join(str(v) for v in sorted(SUPPORTED_PLUGIN_API_VERSIONS))
        errors.append(
            f"manifest plugin_api must be one of: {supported} "
            f"(got {manifest['plugin_api']!r})"
        )
    plugin_api = manifest["plugin_api"]
    if not is_valid_semver(manifest["version"]):
        errors.append(f"manifest version '{manifest['version']}' is not a valid semantic version")
    for key in ("id", "name", "publisher", "license", "description"):
        if not _is_nonempty_str(manifest[key]):
            errors.append(f"manifest key '{key}' must be a non-empty string")
    if not _is_nonempty_str(manifest["requires_app"]):
        errors.append("manifest key 'requires_app' must be a non-empty string")
    else:
        errors.extend(validate_requires_app(manifest["requires_app"]))

    capabilities = manifest["capabilities"]
    if not isinstance(capabilities, list) or not capabilities:
        errors.append("manifest capabilities must be a non-empty list")
    else:
        for capability in capabilities:
            if capability not in KNOWN_CAPABILITIES:
                errors.append(f"unsupported plugin capability: {capability!r}")
    if isinstance(capabilities, list) and plugin_api == 1 and CAPABILITY_LINTER_TOOL in capabilities:
        errors.append("manifest capability 'linter-tool' requires plugin_api 2")
    if plugin_api == 2 and (
        not isinstance(capabilities, list)
        or CAPABILITY_LINTER_TOOL not in capabilities
    ):
        errors.append("plugin_api 2 manifests require the 'linter-tool' capability")
    trusted_tool = False
    if plugin_api == 2:
        reason = trusted_tool_error(manifest)
        if reason:
            errors.append(f"unapproved trusted tool: {reason}")
        else:
            trusted_tool = True

    if not isinstance(manifest["entrypoints"], dict):
        errors.append("manifest entrypoints must be a JSON object")
    elif plugin_api == 1 and V2_LINTER_ENTRYPOINT_KEY in manifest["entrypoints"]:
        errors.append(
            f"manifest entrypoint '{V2_LINTER_ENTRYPOINT_KEY}' requires plugin_api 2"
        )
    elif plugin_api == 2:
        linter_entry = manifest["entrypoints"].get(V2_LINTER_ENTRYPOINT_KEY)
        if not isinstance(linter_entry, str) or not linter_entry.strip():
            errors.append(
                f"plugin_api 2 manifests need entrypoint '{V2_LINTER_ENTRYPOINT_KEY}' "
                "pointing at the engine __init__.py"
            )
        else:
            declared_paths = {
                entry.get("path")
                for entry in manifest.get("files", [])
                if isinstance(entry, dict)
            } if isinstance(manifest.get("files"), list) else set()
            if (
                is_safe_relative_path(linter_entry)
                and declared_paths
                and linter_entry not in declared_paths
            ):
                errors.append(
                    f"entrypoint '{V2_LINTER_ENTRYPOINT_KEY}' does not match any "
                    "declared manifest file"
                )
            if not linter_entry.endswith("/__init__.py"):
                errors.append(
                    f"manifest entrypoint '{V2_LINTER_ENTRYPOINT_KEY}' must point "
                    "to a package __init__.py"
                )
    engine_id = manifest["entrypoints"].get("engine") if isinstance(manifest["entrypoints"], dict) else None
    if engine_id is not None and engine_id not in TRUSTED_DECLARATIVE_ENGINES:
        errors.append(f"unknown declarative engine ID: {engine_id!r}")

    # Optional ui_contributions validation
    if "ui_contributions" in manifest:
        from hpc_gui.plugins.ui_contributions import validate_ui_contributions_dict

        ui_errors = validate_ui_contributions_dict(manifest["ui_contributions"])
        errors.extend(f"ui_contributions: {e}" for e in ui_errors)

    files = manifest["files"]
    if not isinstance(files, list) or not files:
        errors.append("manifest files must be a non-empty list")
        return errors
    seen_paths: set[str] = set()
    for entry in files:
        if not isinstance(entry, dict):
            errors.append("each manifest file entry must be a JSON object")
            continue
        path = entry.get("path")
        if not is_safe_relative_path(path):
            errors.append(f"unsafe or invalid manifest file path: {path!r}")
        elif path in seen_paths:
            errors.append(f"duplicate manifest file path: {path}")
        else:
            seen_paths.add(str(path))
        sha256 = entry.get("sha256")
        if not isinstance(sha256, str) or len(sha256) != 64 or any(c not in "0123456789abcdef" for c in sha256):
            errors.append(f"manifest file '{path}' needs a 64-char lowercase hex sha256")
        size = entry.get("size")
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            errors.append(f"manifest file '{path}' needs a non-negative integer size")
        role = entry.get("role")
        if role not in KNOWN_FILE_ROLES:
            errors.append(f"unsupported manifest file role: {role!r}")
        suffix = PurePosixPath(str(path)).suffix.lower()
        executable_engine_file = trusted_tool and role == V2_LINTER_ENGINE_ROLE and suffix == ".py"
        if suffix and suffix not in ALLOWED_PAYLOAD_SUFFIXES and not executable_engine_file:
            errors.append(
                f"manifest file '{path}' has a forbidden executable-looking extension '{suffix}'"
            )
        if role == V2_LINTER_ENGINE_ROLE and not trusted_tool:
            errors.append(
                f"manifest file '{path}' uses forbidden executable role '{V2_LINTER_ENGINE_ROLE}'"
            )
        if role in {V2_LINTER_ENGINE_ROLE, V2_LINTER_DATA_ROLE} and plugin_api != 2:
            errors.append(
                f"manifest file '{path}' uses v2 role '{role}' but plugin_api is not 2"
            )
        if role == V2_LINTER_DATA_ROLE and suffix not in {".json", ".md", ".txt"}:
            errors.append(
                f"manifest file '{path}' uses role '{V2_LINTER_DATA_ROLE}' with "
                f"unsupported extension '{suffix}'"
            )
    return errors


def validate_cluster_profile_dict(profile: Any) -> list[str]:
    """Validate a raw cluster-profile mapping; returns problems."""
    if not isinstance(profile, dict):
        return ["cluster profile must be a JSON object"]
    errors: list[str] = []
    for key in CLUSTER_PROFILE_REQUIRED_KEYS:
        if key not in profile:
            errors.append(f"cluster profile is missing required key '{key}'")
    if errors:
        return errors
    if profile["schema_version"] not in (1, 2):
        errors.append("cluster profile schema_version must be 1 or 2")
    if not _is_nonempty_str(profile["profile_id"]):
        errors.append("cluster profile 'profile_id' must be a non-empty string")
    if not _is_nonempty_str(profile["name"]):
        errors.append("cluster profile 'name' must be a non-empty string")
    if profile["scheduler"] not in KNOWN_SCHEDULERS:
        errors.append(f"unsupported scheduler: {profile['scheduler']!r}")

    if profile["schema_version"] == 2:
        unknown = set(profile) - set(CLUSTER_PROFILE_REQUIRED_KEYS) - V2_PROFILE_SECTIONS
        errors.extend(f"cluster profile has unknown key '{key}'" for key in sorted(unknown))
        for section_key in V2_PROFILE_SECTIONS - {"description", "paths", "commands", "storage", "quota_sources"}:
            section = profile.get(section_key)
            if section is not None and not isinstance(section, dict):
                errors.append(f"cluster profile '{section_key}' must be an object")
        for section_key in ("storage", "quota_sources"):
            section = profile.get(section_key)
            if section is not None and not isinstance(section, list):
                errors.append(f"cluster profile '{section_key}' must be a list")
            elif isinstance(section, list):
                for index, item in enumerate(section):
                    if not isinstance(item, dict):
                        errors.append(f"cluster profile '{section_key}[{index}]' must be an object")
                        continue
                    if not _is_nonempty_str(item.get("id")):
                        errors.append(f"cluster profile '{section_key}[{index}]' needs a non-empty id")
                    if section_key == "storage" and not _is_nonempty_str(item.get("label")):
                        errors.append(f"cluster profile 'storage[{index}]' needs a non-empty label")

    for section_key in ("paths", "commands"):
        section = profile.get(section_key)
        if section is None:
            continue
        if not isinstance(section, dict):
            errors.append(f"cluster profile '{section_key}' must be a JSON object")
            continue
        for value in section.values():
            if not isinstance(value, str):
                errors.append(f"cluster profile '{section_key}' values must be strings")
                break

    commands = profile.get("commands")
    if isinstance(commands, dict):
        for key, value in commands.items():
            if not isinstance(value, str):
                continue
            if key not in _TRUSTED_SLURM_COMMANDS or value != _TRUSTED_SLURM_COMMANDS[key]:
                errors.append(f"cluster profile command '{key}' is not an application-owned Slurm operation")
                continue
            for placeholder in _PLACEHOLDER_RE.findall(value):
                if placeholder not in KNOWN_COMMAND_PLACEHOLDERS:
                    errors.append(
                        f"cluster profile command '{key}' uses unknown placeholder "
                        f"{{{placeholder}}}"
                    )
    return errors


REGISTRY_ENTRY_REQUIRED_KEYS = (
    "id",
    "name",
    "version",
    "plugin_api",
    "type",
    "description",
    "publisher",
    "requires_app",
    "manifest_path",
    "manifest_sha256",
    "official",
)

REGISTRY_PLUGIN_TYPES = frozenset(
    {
        "cluster-profile",
        "lint-rules",
        "job-template",
        "application-tools",
        "linter-tool",
    }
)
DISCOVERABLE_PLUGIN_API_VERSIONS = frozenset({1, 2})


def _is_sha256_hex(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
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
        identity = (str(entry["id"]), str(entry["version"]))
        if identity in seen:
            errors.append(f"{label}: duplicate (id, version) pair in registry")
        seen.add(identity)
    return errors

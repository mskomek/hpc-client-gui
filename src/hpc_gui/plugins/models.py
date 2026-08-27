"""Typed models for installed declarative plugins (Plugin API v1)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping


SEMVER_RE = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)
PLUGIN_ID_RE = re.compile(r"^[a-z][a-z0-9]*(?:\.[a-z0-9]+)+$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

PLUGIN_API_VERSION = 1
# Additive generations understood by this release. v1 manifests stay
# exactly as before; v2 adds the opt-in "linter-tool" capability with
# hash-verified engine files (see validator/installer/loader).
SUPPORTED_PLUGIN_API_VERSIONS = frozenset({1, 2})

CAPABILITY_CLUSTER_PROFILE = "cluster-profile"
CAPABILITY_LINT_RULES = "lint-rules"
CAPABILITY_JOB_TEMPLATE = "job-template"
CAPABILITY_APPLICATION_TOOLS = "application-tools"
CAPABILITY_LINTER_TOOL = "linter-tool"

KNOWN_CAPABILITIES = frozenset(
    {
        CAPABILITY_CLUSTER_PROFILE,
        CAPABILITY_LINT_RULES,
        CAPABILITY_JOB_TEMPLATE,
        CAPABILITY_APPLICATION_TOOLS,
        CAPABILITY_LINTER_TOOL,
    }
)

KNOWN_FILE_ROLES = frozenset(
    {
        "cluster-profile",
        "lint-index",
        "lint-rules",
        "template-index",
        "template-content",
        "documentation",
        # Plugin API v2 linter-tool roles:
        "linter-engine",
        "linter-data",
    }
)


@dataclass(frozen=True)
class PluginFile:
    path: str
    sha256: str
    size: int
    role: str


@dataclass(frozen=True)
class PluginManifest:
    schema_version: int
    plugin_api: int
    id: str
    name: str
    version: str
    publisher: str
    license: str
    description: str
    requires_app: str
    capabilities: tuple[str, ...]
    entrypoints: Mapping[str, Any]
    files: tuple[PluginFile, ...]


@dataclass(frozen=True)
class ClusterProfileDefinition:
    profile_id: str
    name: str
    scheduler: str
    paths: Mapping[str, str] = field(default_factory=dict)
    commands: Mapping[str, str] = field(default_factory=dict)
    description: str = ""

    def to_system_settings(self) -> dict[str, str]:
        """Map the declarative profile onto app system-settings keys.

        Only known scheduler command keys are transferred; unknown keys are
        dropped so a malformed plugin cannot inject arbitrary settings.
        """
        from hpc_gui.config.system_profile import SYSTEM_SETTING_COMMAND_KEYS

        settings = {"name": self.name}
        for key in ("scratch_dir", "home_dir"):
            value = self.paths.get(key)
            if isinstance(value, str):
                settings[key] = value
        for key in SYSTEM_SETTING_COMMAND_KEYS:
            value = self.commands.get(key)
            if isinstance(value, str) and value.strip():
                settings[key] = value
        return settings


@dataclass(frozen=True)
class InstalledPlugin:
    manifest: PluginManifest
    directory: Path
    cluster_profiles: tuple[ClusterProfileDefinition, ...] = ()
    lint_index: Mapping[str, Any] | None = None
    job_templates_index: Mapping[str, Any] | None = None
    # Plugin API v2 linter-tool entrypoint: {"module": "<rel path .py>"}.
    # The engine is NOT imported here - see plugins/linter_tools.py.
    linter_engine: Mapping[str, Any] | None = None


def is_valid_semver(value: Any) -> bool:
    return isinstance(value, str) and bool(SEMVER_RE.fullmatch(value))


def is_safe_relative_path(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False
    if "\\" in value or value.startswith("/"):
        return False
    if re.match(r"^[A-Za-z]:", value):
        return False
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", value):
        return False
    segments = value.split("/")
    return all(segment not in ("", "..") for segment in segments)

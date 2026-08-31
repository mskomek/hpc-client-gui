"""Typed models for installed declarative plugins."""

from __future__ import annotations

import re
from urllib.parse import unquote
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping


SEMVER_RE = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)
PLUGIN_ID_RE = re.compile(r"^[a-z][a-z0-9]*(?:\.[a-z0-9]+)+$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
STORAGE_KINDS = frozenset({"home", "scratch", "project", "custom", "node-local"})
STORAGE_ACCESS_CONTEXTS = frozenset({"login-node", "shared", "compute-node", "unknown"})
_STORAGE_PLACEHOLDER_RE = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")

PLUGIN_API_VERSION = 1
# The legacy numeric marker 2 is accepted only after the application-owned
# trusted-tool policy approves the exact ANSYS identity.
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
    schema_version: int = 1
    metadata: Mapping[str, Any] = field(default_factory=dict)
    site: Mapping[str, Any] = field(default_factory=dict)
    access: Mapping[str, Any] = field(default_factory=dict)
    requirements: Mapping[str, Any] = field(default_factory=dict)
    scheduler_hints: Mapping[str, Any] = field(default_factory=dict)
    software: Mapping[str, Any] = field(default_factory=dict)
    storage: tuple[Mapping[str, Any], ...] = ()
    quota_sources: tuple[Mapping[str, Any], ...] = ()

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

    def visible_storage_areas(self) -> tuple[Mapping[str, Any], ...]:
        """Return configured storage rows suitable for a path card."""
        visible: list[Mapping[str, Any]] = []
        for area in self.storage:
            path = str(area.get("path_template") or "").strip()
            resolver = area.get("resolver")
            if (not path and not isinstance(resolver, Mapping)) or area.get("enabled") is False:
                continue
            visible.append(area)
        return tuple(visible)


def build_cluster_profile(raw: Mapping[str, Any]) -> ClusterProfileDefinition:
    """Build a validated profile without discarding v2 structured sections."""
    return ClusterProfileDefinition(
        profile_id=str(raw["profile_id"]),
        name=str(raw["name"]),
        scheduler=str(raw["scheduler"]),
        paths={key: value for key, value in (raw.get("paths") or {}).items() if isinstance(value, str)},
        commands={key: value for key, value in (raw.get("commands") or {}).items() if isinstance(value, str)},
        description=str(raw.get("description") or ""),
        schema_version=int(raw.get("schema_version", 1)),
        metadata=dict(raw.get("metadata") or {}),
        site=dict(raw.get("site") or {}),
        access=dict(raw.get("access") or {}),
        requirements=dict(raw.get("requirements") or {}),
        scheduler_hints=dict(raw.get("scheduler_hints") or {}),
        software=dict(raw.get("software") or {}),
        storage=tuple(dict(item) for item in (raw.get("storage") or [])),
        quota_sources=tuple(dict(item) for item in (raw.get("quota_sources") or [])),
    )


def validate_storage_policy(policy: Mapping[str, Any] | None) -> str | None:
    """Validate the small policy subset edited by the connection dialog."""
    if not isinstance(policy, Mapping):
        return None
    retention = policy.get("retention_days")
    if retention is not None and (not isinstance(retention, int) or isinstance(retention, bool) or retention < 0):
        return "retention_days must be a non-negative integer"
    source_url = str(policy.get("documentation_url") or "").strip()
    if source_url and not source_url.startswith("https://"):
        return "documentation_url must use HTTPS"
    return None


def validate_storage_area(area: Mapping[str, Any] | None) -> str | None:
    """Validate passive storage metadata before it is saved locally."""
    if not isinstance(area, Mapping):
        return "storage area must be an object"
    if not isinstance(area.get("id"), str) or not area["id"].strip():
        return "storage area needs an id"
    if not isinstance(area.get("label"), str) or not area["label"].strip():
        return "storage area needs a label"
    kind = area.get("kind", "custom")
    if kind not in STORAGE_KINDS:
        return "storage area kind is unsupported"
    context = area.get("access_context", "unknown")
    if context not in STORAGE_ACCESS_CONTEXTS:
        return "storage access context is unsupported"
    path = str(area.get("path_template") or "")
    if any(character in path for character in "\r\n;|&`$()<>"):
        return "storage path contains unsupported command syntax"
    if any(name not in {"user", "user_first", "project", "account"} for name in _STORAGE_PLACEHOLDER_RE.findall(path)):
        return "storage path uses an unsupported placeholder"
    return validate_storage_policy(area.get("policy"))


@dataclass(frozen=True)
class InstalledPlugin:
    manifest: PluginManifest
    directory: Path
    cluster_profiles: tuple[ClusterProfileDefinition, ...] = ()
    lint_index: Mapping[str, Any] | None = None
    job_templates_index: Mapping[str, Any] | None = None
    # Reserved for an application-owned declarative engine descriptor.
    linter_engine: Mapping[str, Any] | None = None


def is_valid_semver(value: Any) -> bool:
    return isinstance(value, str) and bool(SEMVER_RE.fullmatch(value))


def is_safe_relative_path(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False
    decoded = unquote(value)
    if decoded != value or "\\" in decoded or decoded.startswith("/"):
        return False
    if re.match(r"^[A-Za-z]:", value):
        return False
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", value):
        return False
    segments = decoded.split("/")
    return all(segment not in ("", "..") for segment in segments)

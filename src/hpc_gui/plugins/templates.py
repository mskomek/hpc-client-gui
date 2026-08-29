"""Adapter from installed cluster-profile plugins to system templates.

UI-independent: the connection dialog consumes the same normalized
settings shape it already knows, plus optional provenance metadata.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from hpc_gui import __version__
from hpc_gui.plugins.loader import load_installed_plugins


@dataclass(frozen=True)
class PluginSystemTemplate:
    settings: dict[str, str]
    provenance: dict[str, str] = field(default_factory=dict)
    structured: dict[str, Any] = field(default_factory=dict)


def installed_cluster_template_groups(
    root: str | Path | None = None,
    app_version: str = __version__,
) -> dict[str, list[PluginSystemTemplate]]:
    """Return system-template groups provided by installed plugins.

    Invalid or incompatible plugins are skipped by the loader; they never
    appear here. Grouping is by plugin display name.
    """
    result = load_installed_plugins(root=root, app_version=app_version)
    groups: dict[str, list[PluginSystemTemplate]] = {}
    for installed in result.plugins:
        group_name = installed.manifest.name or installed.manifest.id
        for profile in installed.cluster_profiles:
            groups.setdefault(group_name, []).append(
                PluginSystemTemplate(
                    settings=profile.to_system_settings(),
                    provenance={
                        "kind": "plugin",
                        "plugin_id": installed.manifest.id,
                        "plugin_version": installed.manifest.version,
                        "profile_id": profile.profile_id,
                    },
                    structured={
                        "schema_version": profile.schema_version,
                        "metadata": dict(profile.metadata),
                        "site": dict(profile.site),
                        "scheduler_hints": dict(profile.scheduler_hints),
                        "software": dict(profile.software),
                        "storage": [dict(item) for item in profile.storage],
                        "quota_sources": [dict(item) for item in profile.quota_sources],
                    },
                )
            )
    return groups

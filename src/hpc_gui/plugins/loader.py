"""Local loader for installed declarative plugins.

The loader never executes plugin content and performs no network access.
A malformed single plugin is recorded as a problem and skipped so the
application can still start with the remaining (or zero) plugins.

Each active version is also re-validated locally (trusted manifest hash +
per-file size/SHA-256 + no undeclared extra files). Legacy installs are
migrated once via trust-on-first-use verification, which atomically records
the manifest hash as the initial trust anchor.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from hpc_gui import __version__
from hpc_gui.plugins.compatibility import is_app_compatible
from hpc_gui.plugins.integrity import (
    REINSTALL_HINT,
    IntegrityError,
    ensure_trusted_hash,
    verify_installed_version,
)
from hpc_gui.plugins.models import (
    PLUGIN_API_VERSION,
    ClusterProfileDefinition,
    InstalledPlugin,
    PluginFile,
    PluginManifest,
)
from hpc_gui.plugins.storage import (
    MANIFEST_NAME,
    plugin_package_dir,
    read_active_versions,
    read_disabled_ids,
)
from hpc_gui.plugins.validator import validate_cluster_profile_dict, validate_manifest_dict

logger = logging.getLogger(__name__)


@dataclass
class PluginProblem:
    plugin_id: str
    version: str
    reason: str


@dataclass
class PluginLoadResult:
    plugins: list[InstalledPlugin] = field(default_factory=list)
    problems: list[PluginProblem] = field(default_factory=list)


def _load_json(path: Path) -> tuple[Any | None, str | None]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle), None
    except FileNotFoundError:
        return None, f"file not found: {path.name}"
    except json.JSONDecodeError as exc:
        return None, f"invalid JSON in {path.name}: {exc}"
    except OSError as exc:
        return None, f"cannot read {path.name}: {exc}"


def _build_manifest(raw: Any) -> tuple[PluginManifest | None, str | None]:
    errors = validate_manifest_dict(raw)
    if errors:
        return None, "; ".join(errors)
    files = tuple(
        PluginFile(
            path=entry["path"],
            sha256=entry["sha256"],
            size=entry["size"],
            role=entry["role"],
        )
        for entry in raw["files"]
    )
    manifest = PluginManifest(
        schema_version=raw["schema_version"],
        plugin_api=raw["plugin_api"],
        id=raw["id"],
        name=raw["name"],
        version=raw["version"],
        publisher=raw["publisher"],
        license=raw["license"],
        description=raw["description"],
        requires_app=raw["requires_app"],
        capabilities=tuple(raw["capabilities"]),
        entrypoints=dict(raw.get("entrypoints") or {}),
        files=files,
    )
    return manifest, None


def _build_profile(raw: Any) -> tuple[ClusterProfileDefinition | None, str | None]:
    errors = validate_cluster_profile_dict(raw)
    if errors:
        return None, "; ".join(errors)
    profile = ClusterProfileDefinition(
        profile_id=str(raw["profile_id"]),
        name=str(raw["name"]),
        scheduler=str(raw["scheduler"]),
        paths={
            key: value
            for key, value in (raw.get("paths") or {}).items()
            if isinstance(value, str)
        },
        commands={
            key: value
            for key, value in (raw.get("commands") or {}).items()
            if isinstance(value, str)
        },
        description=str(raw.get("description") or ""),
    )
    return profile, None


def load_installed_plugins(
    root: str | Path | None = None,
    app_version: str = __version__,
) -> PluginLoadResult:
    """Load all active installed plugins from local storage.

    Only locally present declarative payloads are read. Problems are
    collected instead of raised; a broken plugin never blocks startup.
    Legacy records without a stored manifest hash gain one via atomic TOFU
    migration when their files verify cleanly.
    """
    result = PluginLoadResult()

    active = read_active_versions(root)
    if not active:
        return result

    disabled = read_disabled_ids(root)
    id_pattern = re.compile(r"^[a-z][a-z0-9]*(?:\.[a-z0-9]+)+$")
    for plugin_id, version in sorted(active.items()):
        if plugin_id in disabled:
            # Disabled plugins stay installed but contribute nothing.
            continue
        if not id_pattern.fullmatch(plugin_id) or "/" in version or "\\" in version or ".." in version:
            result.problems.append(
                PluginProblem(plugin_id=plugin_id, version=version, reason="unsafe plugin id or version")
            )
            continue

        package_dir = plugin_package_dir(plugin_id, version, root)
        raw_manifest, error = _load_json(package_dir / MANIFEST_NAME)
        if error:
            result.problems.append(PluginProblem(plugin_id, version, error))
            continue

        manifest, error = _build_manifest(raw_manifest)
        if error or manifest is None:
            result.problems.append(PluginProblem(plugin_id, version, f"invalid manifest: {error}"))
            continue

        if manifest.id != plugin_id or manifest.version != version:
            result.problems.append(
                PluginProblem(
                    plugin_id,
                    version,
                    "manifest identity does not match the active index entry",
                )
            )
            continue
        if manifest.plugin_api != PLUGIN_API_VERSION:
            result.problems.append(
                PluginProblem(plugin_id, version, f"unsupported plugin API: {manifest.plugin_api}")
            )
            continue
        if not is_app_compatible(manifest.requires_app, app_version):
            result.problems.append(
                PluginProblem(
                    plugin_id,
                    version,
                    f"incompatible with app {app_version} (requires {manifest.requires_app})",
                )
            )
            continue

        # Local integrity re-validation: compare the manifest with the hash
        # trusted at install time and verify every declared payload file.
        # Legacy records are TOFU-migrated (verified once against their
        # current files, then trusted). A broken version is skipped — never
        # deleted — so the remaining plugins keep loading.
        try:
            trusted_hash = ensure_trusted_hash(plugin_id, version, root=root)
        except IntegrityError as exc:
            result.problems.append(
                PluginProblem(
                    plugin_id,
                    version,
                    f"integrity check failed ({REINSTALL_HINT}): {exc}",
                )
            )
            continue
        errors = verify_installed_version(
            plugin_id, version, root=root, expected_manifest_sha=trusted_hash
        )
        if errors:
            result.problems.append(
                PluginProblem(
                    plugin_id,
                    version,
                    f"integrity check failed ({REINSTALL_HINT}): " + "; ".join(errors),
                )
            )
            continue

        profiles: list[ClusterProfileDefinition] = []
        profile_failed = False
        cluster_entrypoints = manifest.entrypoints.get("cluster_profiles")
        if isinstance(cluster_entrypoints, str):
            cluster_entrypoints = [cluster_entrypoints]
        for rel in cluster_entrypoints or []:
            if not isinstance(rel, str) or not rel or rel.startswith("/") or ".." in rel.split("/"):
                profile_failed = True
                result.problems.append(
                    PluginProblem(plugin_id, version, f"unsafe cluster-profile entrypoint: {rel!r}")
                )
                break
            raw_profile, error = _load_json(package_dir / rel)
            if error:
                profile_failed = True
                result.problems.append(PluginProblem(plugin_id, version, error))
                break
            profile, error = _build_profile(raw_profile)
            if error or profile is None:
                profile_failed = True
                result.problems.append(PluginProblem(plugin_id, version, f"invalid cluster profile: {error}"))
                break
            profiles.append(profile)

        if profile_failed:
            continue

        # Optional lint index entrypoint: a malformed pack is recorded as a
        # problem but does not invalidate the rest of the plugin.
        lint_index_raw = None
        lint_rel = manifest.entrypoints.get("lint_index")
        if isinstance(lint_rel, str) and lint_rel:
            if lint_rel.startswith("/") or ".." in lint_rel.split("/"):
                result.problems.append(
                    PluginProblem(plugin_id, version, f"unsafe lint entrypoint: {lint_rel!r}")
                )
                continue
            raw_pack, error = _load_json(package_dir / lint_rel)
            if error:
                result.problems.append(PluginProblem(plugin_id, version, f"lint index: {error}"))
                continue
            if not isinstance(raw_pack, dict) or raw_pack.get("schema_version") != 1:
                result.problems.append(
                    PluginProblem(plugin_id, version, "lint index: unsupported schema_version")
                )
                continue
            lint_index_raw = raw_pack

        # Optional job-template index entrypoint (same isolation rules).
        templates_index_raw = None
        templates_rel = manifest.entrypoints.get("job_templates")
        if isinstance(templates_rel, list):
            templates_rel = templates_rel[0] if templates_rel else None
        if isinstance(templates_rel, str) and templates_rel:
            if templates_rel.startswith("/") or ".." in templates_rel.split("/"):
                result.problems.append(
                    PluginProblem(
                        plugin_id, version, f"unsafe job-template entrypoint: {templates_rel!r}"
                    )
                )
                continue
            raw_templates, error = _load_json(package_dir / templates_rel)
            if error:
                result.problems.append(
                    PluginProblem(plugin_id, version, f"job template index: {error}")
                )
                continue
            if not isinstance(raw_templates, dict) or raw_templates.get("schema_version") != 1:
                result.problems.append(
                    PluginProblem(
                        plugin_id, version, "job template index: unsupported schema_version"
                    )
                )
                continue
            templates_index_raw = raw_templates

        result.plugins.append(
            InstalledPlugin(
                manifest=manifest,
                directory=package_dir,
                cluster_profiles=tuple(profiles),
                lint_index=lint_index_raw,
                job_templates_index=templates_index_raw,
            )
        )

    if result.problems:
        logger.warning(
            "Skipped %d invalid installed plugin(s): %s",
            len(result.problems),
            "; ".join(f"{p.plugin_id}@{p.version}: {p.reason}" for p in result.problems),
        )
    return result

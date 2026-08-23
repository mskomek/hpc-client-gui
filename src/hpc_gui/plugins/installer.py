"""Installer for official declarative plugins (exact-file protocol).

Implements the strict install algorithm:

1. resolve the validated registry entry;
2. download exactly the manifest and verify its SHA-256 against the registry;
3. validate manifest identity, plugin API, app compatibility, capabilities;
4. stage only the manifest-declared files with per-file size/SHA-256 checks;
5. validate capability entrypoints;
6. publish staging into the immutable version directory — a version that is
   already present is reused only when its verified contents match the
   manifest byte-for-byte; conflicting or corrupt versions are never
   overwritten (best-effort atomicity via same-volume rename);
7. record installed metadata and activate — only after everything verified.

Any failure before activation cleans up staging and leaves previous state
untouched; published version directories are never deleted first. All
functions are synchronous/UI-independent.
"""

from __future__ import annotations

import hashlib
import json
import logging
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hpc_gui import __version__
from hpc_gui.plugins.compatibility import is_app_compatible
from hpc_gui.plugins.downloader import (
    DownloadError,
    compute_local_sha256,
    download_exact_file,
    validate_payload_rel_path,
)
from hpc_gui.plugins.models import (
    PLUGIN_API_VERSION,
    ClusterProfileDefinition,
    InstalledPlugin,
    PluginFile,
    PluginManifest,
)
from hpc_gui.plugins.registry_client import (
    DEFAULT_TIMEOUT_SECONDS,
    FILE_MAX_BYTES,
    MANIFEST_MAX_BYTES,
    OFFICIAL_RAW_BASE,
    PLUGIN_MAX_FILE_COUNT,
    PLUGIN_VERSION_MAX_BYTES,
    FetchFn,
    RegistryError,
    default_fetcher,
)
from hpc_gui.plugins.state import read_active_versions, record_installed_version
from hpc_gui.plugins.storage import (
    MANIFEST_NAME,
    packages_dir,
    plugins_root,
    write_active_versions,
)
from hpc_gui.plugins.validator import (
    KNOWN_CAPABILITIES,
    validate_cluster_profile_dict,
    validate_manifest_dict,
)

STAGING_DIR_NAME = ".staging"

logger = logging.getLogger(__name__)


class InstallError(RuntimeError):
    """Raised when a plugin installation cannot complete safely."""


@dataclass(frozen=True)
class InstallResult:
    installed: InstalledPlugin
    activated: bool


def _fetch_bytes(
    fetch: FetchFn, url: str, max_bytes: int, error_prefix: str
) -> bytes:
    try:
        return fetch(url, max_bytes)
    except (DownloadError, RegistryError):
        raise
    except Exception as exc:
        raise InstallError(f"{error_prefix}: {exc}") from exc


def _parse_manifest(payload: bytes) -> dict[str, Any]:
    if len(payload) > MANIFEST_MAX_BYTES:
        raise InstallError("Manifest exceeds the size limit.")
    try:
        raw = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InstallError(f"Manifest is not valid UTF-8 JSON: {exc}") from exc
    problems = validate_manifest_dict(raw)
    if problems:
        raise InstallError("Invalid manifest: " + "; ".join(problems))
    return raw


def _build_manifest(raw: dict[str, Any]) -> PluginManifest:
    files = tuple(
        PluginFile(
            path=entry["path"],
            sha256=entry["sha256"],
            size=entry["size"],
            role=entry["role"],
        )
        for entry in raw["files"]
    )
    return PluginManifest(
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


def _check_entrypoint_payloads(staging_dir: Path, manifest: PluginManifest) -> tuple[ClusterProfileDefinition, ...]:
    profiles: list[ClusterProfileDefinition] = []
    cluster_entrypoints = manifest.entrypoints.get("cluster_profiles")
    declared = {entry.path for entry in manifest.files}
    if isinstance(cluster_entrypoints, str):
        cluster_entrypoints = [cluster_entrypoints]
    for rel in cluster_entrypoints or []:
        validate_payload_rel_path(rel)
        if rel not in declared:
            raise InstallError(f"Entrypoint '{rel}' is not declared in manifest.files.")
        payload_path = staging_dir / rel
        try:
            raw_profile = json.loads(payload_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise InstallError(f"Cannot read cluster profile '{rel}': {exc}") from exc
        problems = validate_cluster_profile_dict(raw_profile)
        if problems:
            raise InstallError(f"Invalid cluster profile '{rel}': " + "; ".join(problems))
        profiles.append(
            ClusterProfileDefinition(
                profile_id=str(raw_profile["profile_id"]),
                name=str(raw_profile["name"]),
                scheduler=str(raw_profile["scheduler"]),
                paths={
                    key: value
                    for key, value in (raw_profile.get("paths") or {}).items()
                    if isinstance(value, str)
                },
                commands={
                    key: value
                    for key, value in (raw_profile.get("commands") or {}).items()
                    if isinstance(value, str)
                },
                description=str(raw_profile.get("description") or ""),
            )
        )
    return tuple(profiles)


def _existing_install_matches(
    final_dir: Path,
    manifest: PluginManifest,
    expected_manifest_sha: str | None,
) -> bool:
    """Return True only if the installed version is byte-identical to the
    verified incoming payload. Published versions are immutable, so a
    mismatch means conflict or corruption — never a silent overwrite."""
    try:
        installed_manifest = final_dir / MANIFEST_NAME
        if not installed_manifest.is_file():
            return False
        if (
            expected_manifest_sha
            and compute_local_sha256(installed_manifest) != expected_manifest_sha
        ):
            return False
        declared = {entry.path for entry in manifest.files}
        for existing in final_dir.rglob("*"):
            if not existing.is_file():
                continue
            rel = existing.relative_to(final_dir).as_posix()
            if rel == MANIFEST_NAME or rel in declared:
                continue
            return False  # undeclared extra file: treat as corruption
        for entry in manifest.files:
            path = final_dir / entry.path
            if not path.is_file():
                return False
            if path.stat().st_size != entry.size:
                return False
            if compute_local_sha256(path) != entry.sha256:
                return False
    except OSError:
        return False
    return True


def install_plugin_from_registry(
    registry_entry: dict[str, Any],
    *,
    root: str | Path | None = None,
    app_version: str = __version__,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    fetcher: FetchFn | None = None,
) -> InstallResult:
    """Install one plugin version described by a validated registry entry."""
    _ = timeout  # default_fetcher owns its timeout; kept for interface parity
    fetch = fetcher or default_fetcher

    plugin_id = registry_entry.get("id")
    version = registry_entry.get("version")
    manifest_rel = registry_entry.get("manifest_path")
    expected_manifest_sha = registry_entry.get("manifest_sha256")
    if not (isinstance(plugin_id, str) and isinstance(version, str) and isinstance(manifest_rel, str)):
        raise InstallError("Registry entry is incomplete.")

    logger.info("Installing plugin %s@%s", plugin_id, version)

    # Step 2: exact manifest download + SHA verification (steps 2-3).
    url = OFFICIAL_RAW_BASE + manifest_rel
    payload = _fetch_bytes(fetch, url, MANIFEST_MAX_BYTES, "Cannot download the plugin manifest")
    actual_sha = hashlib.sha256(payload).hexdigest()
    if actual_sha != expected_manifest_sha:
        raise InstallError(
            f"Manifest SHA-256 mismatch for {plugin_id} (expected {expected_manifest_sha})."
        )

    # Step 4: parse/validate manifest and identity/compatibility.
    raw_manifest = _parse_manifest(payload)
    manifest = _build_manifest(raw_manifest)
    if manifest.id != plugin_id or manifest.version != version:
        raise InstallError("Manifest identity does not match the registry entry.")
    if manifest.plugin_api != PLUGIN_API_VERSION:
        raise InstallError(f"Unsupported plugin API version: {manifest.plugin_api}")
    if not is_app_compatible(manifest.requires_app, app_version):
        raise InstallError(
            f"Plugin requires app {manifest.requires_app}; running {app_version}."
        )
    unsupported = [c for c in manifest.capabilities if c not in KNOWN_CAPABILITIES]
    if unsupported:
        raise InstallError(f"Unsupported capabilities: {', '.join(unsupported)}")
    if len(manifest.files) > PLUGIN_MAX_FILE_COUNT:
        raise InstallError("Manifest declares too many files.")

    base_rel_dir = manifest_rel.rsplit("/", 1)[0] if "/" in manifest_rel else ""
    total_bytes = sum(entry.size for entry in manifest.files)
    if total_bytes > PLUGIN_VERSION_MAX_BYTES:
        raise InstallError("Plugin version exceeds the total size limit.")

    # Step 5: staging directory under <root>/.staging (same volume as packages).
    base_root = Path(plugins_root(root))
    staging_root = base_root / STAGING_DIR_NAME
    staging_dir = staging_root / f"{plugin_id}-{version}-{uuid.uuid4().hex[:8]}"
    try:
        try:
            staging_dir.mkdir(parents=True)
        except OSError as exc:
            raise InstallError(f"Cannot create staging directory: {exc}") from exc

        # Steps 6-7: exact-file downloads with per-file verification.
        # The verified manifest itself is part of the installed package.
        manifest_target = staging_dir / MANIFEST_NAME
        manifest_target.parent.mkdir(parents=True, exist_ok=True)
        manifest_part = manifest_target.with_name(MANIFEST_NAME + ".part")
        manifest_part.write_bytes(payload)
        manifest_part.replace(manifest_target)

        downloaded = 0
        for file_entry in manifest.files:
            rel = file_entry.path
            validate_payload_rel_path(rel)
            remote_rel = f"{base_rel_dir}/{rel}" if base_rel_dir else rel
            try:
                destination = download_exact_file(
                    rel_path=remote_rel,
                    destination_dir=staging_dir,
                    expected_sha256=file_entry.sha256,
                    expected_size=file_entry.size,
                    max_bytes=FILE_MAX_BYTES,
                    fetcher=fetch,
                )
            except DownloadError as exc:
                raise InstallError(str(exc)) from exc
            local_rel = destination.relative_to(staging_dir).as_posix()
            if local_rel != rel:
                # The remote layout mirrors the manifest-relative layout.
                target = staging_dir / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(destination), str(target))
            downloaded += 1

        if downloaded != len(manifest.files):  # pragma: no cover - defensive
            raise InstallError("Not all declared files were downloaded.")

        # Local re-verification of every staged byte before activation.
        for file_entry in manifest.files:
            staged = staging_dir / file_entry.path
            if not staged.is_file():
                raise InstallError(f"Staged file missing after download: {file_entry.path}")
            if staged.stat().st_size != file_entry.size:
                raise InstallError(f"Staged size mismatch: {file_entry.path}")
            if compute_local_sha256(staged) != file_entry.sha256:
                raise InstallError(f"Staged SHA-256 mismatch: {file_entry.path}")

        profiles = _check_entrypoint_payloads(staging_dir, manifest)

        # Step 8: publish staging into the immutable version directory.
        # Staging and packages share the same filesystem/volume, so the
        # rename below is atomic on supported platforms. An existing
        # version directory is never deleted first: verified-identical
        # content is reused idempotently, anything else is a conflict.
        final_dir = packages_dir(root) / plugin_id / version
        if final_dir.exists():
            if _existing_install_matches(final_dir, manifest, expected_manifest_sha):
                logger.info(
                    "Reusing existing verified install of %s@%s", plugin_id, version
                )
            else:
                raise InstallError(
                    f"Version directory for {plugin_id}@{version} already exists "
                    "with different or corrupt contents. Published plugin "
                    "versions are immutable; remove the conflicting version "
                    "explicitly before reinstalling. The previously active "
                    "version was left untouched."
                )
        else:
            final_dir.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(staging_dir), str(final_dir))

        installed_plugin = InstalledPlugin(
            manifest=manifest,
            directory=final_dir.resolve(),
            cluster_profiles=profiles,
        )

        # Steps 9-10: record state and activate only after full success.
        previous_active = read_active_versions(root).get(plugin_id)
        record_installed_version(plugin_id, version, root=root, activate=True)

        # Post-activation runtime validation with automatic rollback: the
        # active pointer returns to the previous version if anything fails.
        from hpc_gui.plugins.loader import load_installed_plugins

        loaded = load_installed_plugins(root=root, app_version=app_version)
        activated_ok = any(
            installed.manifest.id == plugin_id and installed.manifest.version == version
            for installed in loaded.plugins
        )
        if not activated_ok:
            logger.warning(
                "Plugin %s@%s failed post-activation validation; rolling back to %s",
                plugin_id,
                version,
                previous_active or "<inactive>",
            )
            if previous_active is not None:
                write_active_versions(
                    {**read_active_versions(root), plugin_id: previous_active}, root=root
                )
                raise InstallError(
                    f"Installed {plugin_id}@{version} failed validation; "
                    f"previous version {previous_active} remains active."
                )
            active_now = read_active_versions(root)
            active_now.pop(plugin_id, None)
            write_active_versions(active_now, root=root)
            raise InstallError(
                f"Installed {plugin_id}@{version} failed validation; plugin deactivated."
            )

        logger.info("Activated plugin %s@%s", plugin_id, version)
        return InstallResult(installed=installed_plugin, activated=True)
    finally:
        if staging_dir.exists():
            shutil.rmtree(staging_dir, ignore_errors=True)

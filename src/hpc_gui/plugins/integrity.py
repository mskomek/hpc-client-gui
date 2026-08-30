"""Local integrity re-validation for installed plugin versions.

Installation verifies every byte before activation, but installed files can
still change afterwards (disk errors, manual edits, malware). This module
re-validates an installed version against its manifest and against the
manifest SHA-256 that was trusted at install time:

1. ``installed.json`` stores the verified manifest SHA-256 per version
   (``manifest_hashes``) plus a ``migrated`` list for legacy records whose
   hash was established by trust-on-first-use verification.
2. Verification compares the on-disk manifest with the trusted hash and then
   checks every declared payload file for presence, exact size, and
   SHA-256. Undeclared extra files inside the immutable version directory
   are rejected.
3. Legacy records without a stored hash are migrated once: their current
   structure and files are verified against the manifest as it exists at
   migration time, and only then is that manifest hash recorded as the
   initial trust anchor. TOFU cannot prove the files were unchanged between
   installation and migration; this limitation is documented.

A failed check never deletes anything; callers skip the broken plugin and
offer reinstallation.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from hpc_gui.plugins.downloader import compute_local_sha256
from hpc_gui.plugins.state import read_installed_state, write_installed_state
from hpc_gui.plugins.storage import MANIFEST_NAME, plugin_package_dir
from hpc_gui.plugins.validator import validate_manifest_dict

logger = logging.getLogger(__name__)

REINSTALL_HINT = "reinstall this plugin from the official registry"


class IntegrityError(RuntimeError):
    """Raised when an installed plugin version fails local verification."""


def compute_manifest_sha256(
    plugin_id: str, version: str, root: str | Path | None = None
) -> str | None:
    """SHA-256 of the installed manifest, or None when it cannot be read."""
    path = plugin_package_dir(plugin_id, version, root) / MANIFEST_NAME
    try:
        return compute_local_sha256(path)
    except OSError:
        return None


def _load_manifest(package_dir: Path) -> tuple[dict | None, list[str]]:
    path = package_dir / MANIFEST_NAME
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, [f"missing {MANIFEST_NAME}"]
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return None, [f"unreadable or invalid {MANIFEST_NAME}: {exc}"]
    if not isinstance(raw, dict):
        return None, [f"invalid {MANIFEST_NAME}: not a JSON object"]
    problems = validate_manifest_dict(raw)
    if problems:
        return None, [f"invalid {MANIFEST_NAME}: {'; '.join(problems)}"]
    return raw, []


def verify_version_dir(
    package_dir: Path,
    *,
    expected_manifest_sha: str | None = None,
) -> list[str]:
    """Verify one installed version directory; returns error strings.

    Checks (in order): trusted manifest hash, manifest validity, per-file
    existence/size/SHA-256, and absence of undeclared extra files.
    """
    errors: list[str] = []
    if package_dir.is_symlink():
        return ["plugin package directory is a symlink"]
    manifest_path = package_dir / MANIFEST_NAME
    if expected_manifest_sha:
        try:
            actual = compute_local_sha256(manifest_path)
        except OSError:
            return [f"missing {MANIFEST_NAME}"]
        if actual != expected_manifest_sha:
            return [
                f"{MANIFEST_NAME} hash mismatch (trusted {expected_manifest_sha[:12]}…)"
            ]

    raw, manifest_errors = _load_manifest(package_dir)
    if raw is None:
        return [*errors, *manifest_errors]

    declared: set[str] = set()
    for entry in raw["files"]:
        rel = str(entry["path"])
        declared.add(rel)
        target = package_dir / rel
        if target.is_symlink():
            errors.append(f"symlink payload is forbidden: {rel}")
            continue
        if not target.is_file():
            errors.append(f"missing payload file: {rel}")
            continue
        try:
            size_ok = target.stat().st_size == entry["size"]
            hash_ok = compute_local_sha256(target) == entry["sha256"]
        except OSError as exc:
            errors.append(f"cannot read {rel}: {exc}")
            continue
        if not size_ok:
            errors.append(f"size mismatch: {rel}")
        elif not hash_ok:
            errors.append(f"sha-256 mismatch: {rel}")

    try:
        for existing in package_dir.rglob("*"):
            if not existing.is_file():
                continue
            rel = existing.relative_to(package_dir).as_posix()
            if rel != MANIFEST_NAME and rel not in declared:
                errors.append(f"unexpected extra file in immutable plugin dir: {rel}")
    except OSError as exc:
        errors.append(f"cannot scan plugin directory: {exc}")
    return errors


def verify_installed_version(
    plugin_id: str,
    version: str,
    root: str | Path | None = None,
    *,
    expected_manifest_sha: str | None = None,
) -> list[str]:
    """Verify an installed plugin version against its recorded trust anchor."""
    if expected_manifest_sha is None:
        state = read_installed_state(root)
        record = state.get(plugin_id, {})
        hashes = record.get("manifest_hashes")
        if isinstance(hashes, dict):
            expected_manifest_sha = hashes.get(version) or None
    errors = verify_version_dir(
        plugin_package_dir(plugin_id, version, root),
        expected_manifest_sha=expected_manifest_sha,
    )
    if errors:
        logger.warning("Integrity check failed for %s@%s: %s", plugin_id, version, "; ".join(errors))
    return errors


def ensure_trusted_hash(
    plugin_id: str,
    version: str,
    root: str | Path | None = None,
    *,
    allow_migration: bool = True,
) -> str:
    """Return the trusted manifest hash for an installed version.

    When the record has no hash yet (legacy install), the current files are
    fully verified against the manifest as found on disk; success records
    that hash as the initial trust anchor (TOFU) and marks the record
    migrated. Failures raise :class:`IntegrityError`.
    """
    state = read_installed_state(root)
    record = state.get(plugin_id)
    if isinstance(record, dict):
        hashes = record.get("manifest_hashes")
        if isinstance(hashes, dict) and hashes.get(version):
            return str(hashes[version])

    package_dir = plugin_package_dir(plugin_id, version, root)
    manifest_sha = compute_manifest_sha256(plugin_id, version, root)
    if not manifest_sha:
        raise IntegrityError(f"{MANIFEST_NAME} missing for {plugin_id}@{version}")
    errors = verify_version_dir(package_dir, expected_manifest_sha=manifest_sha)
    if errors:
        raise IntegrityError(
            f"{plugin_id}@{version} failed verification: " + "; ".join(errors)
        )
    if allow_migration and isinstance(record, dict):
        try:
            mark_migrated(plugin_id, version, manifest_sha, root=root)
        except OSError as exc:
            # Migration is best-effort: loading continues with the verified
            # files; the next load retries the atomic state update.
            logger.warning(
                "Could not persist TOFU migration for %s@%s: %s",
                plugin_id,
                version,
                exc,
            )
    return manifest_sha


def mark_migrated(
    plugin_id: str,
    version: str,
    manifest_sha: str,
    root: str | Path | None = None,
) -> None:
    """Record a verified manifest hash + explicit migrated flag atomically."""
    state = read_installed_state(root)
    record = state.get(plugin_id)
    if not isinstance(record, dict):
        raise IntegrityError(f"No installed.json record for {plugin_id}")
    hashes = record.setdefault("manifest_hashes", {})
    if not isinstance(hashes, dict):
        record["manifest_hashes"] = hashes = {}
    hashes[version] = manifest_sha
    migrated = record.setdefault("migrated", [])
    if isinstance(migrated, list) and version not in migrated:
        migrated.append(version)
    write_installed_state(state, root=root)


def migrate_legacy_records(root: str | Path | None = None) -> list[tuple[str, str]]:
    """TOFU-migrate every legacy installed.json record lacking a hash.

    Each candidate version is verified against its current files before any
    hash is recorded; one broken version never blocks the others. All
    successful updates are persisted with a single atomic write. Returns the
    migrated ``(plugin_id, version)`` pairs.
    """
    state = read_installed_state(root)
    migrated: list[tuple[str, str]] = []
    changed = False
    for plugin_id, record in sorted(state.items()):
        versions = record.get("versions", []) if isinstance(record, dict) else []
        hashes = record.get("manifest_hashes") if isinstance(record, dict) else None
        for version in versions:
            if isinstance(hashes, dict) and hashes.get(version):
                continue
            try:
                sha = ensure_trusted_hash(
                    plugin_id, version, root=root, allow_migration=False
                )
            except IntegrityError as exc:
                logger.warning("TOFU migration skipped %s@%s: %s", plugin_id, version, exc)
                continue
            record_hashes = record.setdefault("manifest_hashes", {})
            record_hashes[version] = sha
            migrated_list = record.setdefault("migrated", [])
            if version not in migrated_list:
                migrated_list.append(version)
            migrated.append((plugin_id, version))
            changed = True
    if changed:
        write_installed_state(state, root=root)
    return migrated

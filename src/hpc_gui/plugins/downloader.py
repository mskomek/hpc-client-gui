"""Exact-file downloader for official plugin payloads.

Only files declared in a validated manifest are downloaded, one by one,
from the official raw base. No repository ZIPs, no Git clones, no tokens.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from hpc_gui.plugins.models import is_safe_relative_path
from hpc_gui.plugins.registry_client import (
    FILE_MAX_BYTES,
    OFFICIAL_RAW_BASE,
    FetchFn,
    RegistryError,
    default_fetcher,
)

# Percent signs are rejected outright so URL building can never reinterpret
# encoded traversal sequences (for example %2e%2e%2f).
_UNSAFE_PATH_CHARS = re.compile(r"[%\x00]")


class DownloadError(RuntimeError):
    """Raised when an exact-file download fails or fails verification."""


def validate_payload_rel_path(rel_path: str) -> None:
    if not isinstance(rel_path, str) or not rel_path:
        raise DownloadError("Empty plugin file path.")
    if _UNSAFE_PATH_CHARS.search(rel_path):
        raise DownloadError(f"Unsafe characters in plugin file path: {rel_path!r}")
    segments = rel_path.split("/")
    if any(segment in ("", ".", "..") for segment in segments):
        raise DownloadError(f"Unsafe path segment in plugin file path: {rel_path!r}")
    if not is_safe_relative_path(rel_path):
        raise DownloadError(f"Unsafe plugin file path: {rel_path!r}")


def payload_url(rel_path: str, raw_base: str = OFFICIAL_RAW_BASE) -> str:
    """Build the exact download URL for a manifest-relative payload path."""
    validate_payload_rel_path(rel_path)
    if not raw_base.startswith("https://") or not raw_base.endswith("/"):
        raise DownloadError("Raw base must be an HTTPS URL ending with '/'.")
    return raw_base + rel_path


def _sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_exact_file(
    *,
    rel_path: str,
    destination_dir: Path,
    expected_sha256: str,
    expected_size: int | None = None,
    max_bytes: int = FILE_MAX_BYTES,
    raw_base: str = OFFICIAL_RAW_BASE,
    fetcher: FetchFn | None = None,
) -> Path:
    """Download one declared payload file into ``destination_dir``.

    The file is written to a ``.part`` temporary first and only moved into
    place after its size and SHA-256 verify.
    """
    url = payload_url(rel_path, raw_base=raw_base)
    fetch = fetcher or (lambda u, limit: default_fetcher(u, limit))

    try:
        payload = fetch(url, max_bytes)
    except DownloadError:
        raise
    except Exception as exc:
        raise DownloadError(f"Cannot download '{rel_path}': {exc}") from exc

    if len(payload) > max_bytes:
        raise DownloadError(f"File '{rel_path}' exceeds the per-file size limit.")
    if expected_size is not None and len(payload) != expected_size:
        raise DownloadError(
            f"File '{rel_path}' has unexpected size {len(payload)} (expected {expected_size})."
        )
    actual_sha256 = hashlib.sha256(payload).hexdigest()
    if actual_sha256 != expected_sha256:
        raise DownloadError(
            f"SHA-256 mismatch for '{rel_path}' (expected {expected_sha256}, got {actual_sha256})."
        )

    destination = destination_dir / rel_path
    staging_root = Path(destination_dir).resolve()
    resolved_parent = destination.parent.resolve()
    try:
        resolved_parent.relative_to(staging_root)
    except ValueError as exc:  # pragma: no cover - guarded by path validation
        raise DownloadError(f"Resolved path escapes the staging root: {rel_path}") from exc

    destination.parent.mkdir(parents=True, exist_ok=True)
    part_file = destination.with_name(destination.name + ".part")
    part_file.write_bytes(payload)
    part_file.replace(destination)
    return destination


def compute_local_sha256(path: Path) -> str:
    """Public helper mirroring verification semantics for staged files."""
    return _sha256_of(path)

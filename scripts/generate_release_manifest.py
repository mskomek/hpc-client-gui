"""Generate a machine-readable MANIFEST.json for a staged release directory.

The manifest covers every staged artifact with size and SHA-256 so users can
verify a complete release offline, and gives the attestation step a stable
inventory. It contains no secret material and no machine-local absolute paths.

Usage:
    python scripts/generate_release_manifest.py --release-dir dist/releases/v1.2.7
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

MANIFEST_NAME = "MANIFEST.json"

_PLATFORM_HINTS = {
    "windows": "windows",
    ".exe": "windows",
    "onedir.zip": "windows",
    "appimage": "linux",
    ".deb": "linux",
    "flatpak": "linux",
}

_FORMAT_HINTS = {
    ".zip": "zip",
    ".sha256": "checksum",
    ".appimage": "appimage",
    ".deb": "deb",
    ".flatpak": "flatpak",
    ".md": "text",
}


def _platform_label(name: str) -> str:
    lowered = name.lower()
    for hint, label in _PLATFORM_HINTS.items():
        if hint in lowered:
            return label
    return "unknown"


def _format_label(name: str) -> str:
    suffix = Path(name).suffix.lower()
    return _FORMAT_HINTS.get(suffix, "data")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_manifest(release_dir: Path, version: str) -> dict:
    artifacts = []
    for path in sorted(release_dir.iterdir(), key=lambda item: item.name):
        if not path.is_file() or path.name == MANIFEST_NAME:
            continue
        artifacts.append(
            {
                "file": path.name,
                "size": path.stat().st_size,
                "sha256": sha256_file(path),
                "platform": _platform_label(path.name),
                "format": _format_label(path.name),
            }
        )
    return {
        "schema": 1,
        "release": version,
        "sbom": None,
        "artifacts": artifacts,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-dir", type=Path, required=True)
    parser.add_argument("--version", default=None, help="defaults to the directory name")
    args = parser.parse_args(argv)

    release_dir = args.release_dir.resolve()
    if not release_dir.is_dir():
        print(f"release directory does not exist: {release_dir}", file=sys.stderr)
        return 2
    version = args.version or release_dir.name

    manifest = build_manifest(release_dir, version)
    if not manifest["artifacts"]:
        print(f"no artifacts found in {release_dir}", file=sys.stderr)
        return 2
    target = release_dir / MANIFEST_NAME
    target.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"MANIFEST: {target} ({len(manifest['artifacts'])} artifacts)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

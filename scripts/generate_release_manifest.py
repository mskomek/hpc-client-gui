"""Generate a machine-readable MANIFEST.json for a staged release directory.

The manifest covers every staged artifact with size and SHA-256 so users can
verify a complete release offline, and gives the attestation step a stable
inventory. It contains no secret material and no machine-local absolute paths.

Usage:
    python scripts/generate_release_manifest.py --release-dir dist/releases/v1.2.7
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import platform
import re
import subprocess
import sys
from pathlib import Path

try:
    from artifact_identity import format_artifact_identity
except ImportError:  # pragma: no cover - direct script execution without scripts/ on sys.path
    from scripts.artifact_identity import format_artifact_identity

ROOT = Path(__file__).resolve().parents[1]
UNKNOWN = "unknown"

MANIFEST_NAME = "MANIFEST.json"

_PLATFORM_HINTS = {
    "windows": "windows",
    ".exe": "windows",
    "onedir.zip": "windows",
    "appimage": "linux",
    ".deb": "linux",
    "flatpak": "linux",
    "macos": "macos",
    ".dmg": "macos",
}

_FORMAT_HINTS = {
    ".zip": "zip",
    ".sha256": "checksum",
    ".appimage": "appimage",
    ".deb": "deb",
    ".flatpak": "flatpak",
    ".dmg": "dmg",
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


def _git_head(repo: Path) -> str:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, check=False, timeout=15
        )
    except Exception:
        return UNKNOWN
    value = proc.stdout.strip()
    if proc.returncode == 0 and re.fullmatch(r"[0-9a-fA-F]{40}", value):
        return value
    return UNKNOWN


def _app_version() -> str:
    try:
        text = (ROOT / "src" / "hpc_gui" / "__init__.py").read_text(encoding="utf-8")
    except OSError:
        return UNKNOWN
    match = re.search(r"""__version__\s*=\s*['"]([^'"]+)['"]""", text)
    return match.group(1) if match else UNKNOWN


def _packager_version() -> str:
    try:
        from importlib import metadata as _metadata

        for dist_name in ("pyinstaller", "pip", "setuptools", "wheel"):
            try:
                return f"{dist_name}=={_metadata.version(dist_name)}"
            except Exception:
                continue
    except Exception:
        pass
    return UNKNOWN


def _dependency_lock_ref() -> str:
    try:
        return sha256_file(ROOT / "requirements-release.lock")
    except OSError:
        return UNKNOWN


def _plugin_commit() -> str:
    sibling = ROOT.parent / "hpc-client-gui-plugins"
    if (sibling / ".git").is_dir():
        return _git_head(sibling)
    return UNKNOWN


def build_manifest(
    release_dir: Path,
    version: str,
    *,
    provenance: dict | None = None,
    build_command: str | None = None,
) -> dict:
    """Build the full 11-field build manifest for a staged release directory.

    Required provenance fields (WAVE_V2_FINAL_04 Workstream B): main commit,
    plugin commit/bundle revision, UTC build timestamp, application version,
    runtime version, packager version, target OS/arch, build command,
    dependency lock/reference, artifact filename and artifact SHA256 (the
    last two per staged artifact).
    """
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
    provenance = dict(provenance) if provenance else {}
    manifest = {
        "schema": 1,
        "release": version,
        "sbom": None,
        "artifacts": artifacts,
        "main_commit": provenance.get("main_commit") or _git_head(ROOT),
        "plugin_commit": provenance.get("plugin_commit") or _plugin_commit(),
        "plugin_bundle_revision": provenance.get("plugin_commit") or _plugin_commit(),
        "build_timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "app_version": _app_version(),
        "python_runtime": platform.python_version(),
        "packager_version": _packager_version(),
        "target_os_arch": f"{platform.system().lower()}/{platform.machine().lower()}",
        "build_command": build_command or " ".join(sys.argv),
        "dependency_lock_sha256": provenance.get("dependency_lock_sha256") or _dependency_lock_ref(),
    }
    return manifest


def identity_headers_for_manifest(manifest: dict) -> list[str]:
    """Render the six-line identity header for every staged artifact."""
    headers = []
    for entry in manifest.get("artifacts", []):
        headers.append(
            format_artifact_identity(
                artifact=entry["file"],
                sha256=entry["sha256"],
                main_sha=manifest.get("main_commit", UNKNOWN),
                plugin_sha=manifest.get("plugin_commit", UNKNOWN),
                version=str(manifest.get("app_version", manifest.get("release", UNKNOWN))),
                os_arch=manifest.get("target_os_arch", UNKNOWN),
            )
        )
    return headers


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-dir", type=Path, required=True)
    parser.add_argument("--version", default=None, help="defaults to the directory name")
    parser.add_argument("--build-command", default=None, help="recorded build command for provenance")
    args = parser.parse_args(argv)

    release_dir = args.release_dir.resolve()
    if not release_dir.is_dir():
        print(f"release directory does not exist: {release_dir}", file=sys.stderr)
        return 2
    version = args.version or release_dir.name

    manifest = build_manifest(release_dir, version, build_command=args.build_command)
    if not manifest["artifacts"]:
        print(f"no artifacts found in {release_dir}", file=sys.stderr)
        return 2
    target = release_dir / MANIFEST_NAME
    target.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    for header in identity_headers_for_manifest(manifest):
        print(header)
        print("---")
    print(f"MANIFEST: {target} ({len(manifest['artifacts'])} artifacts)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


KEY_ID = "release-2026-01"
ASSET_SUFFIXES = (".zip", ".dmg", ".AppImage", ".deb", ".flatpak")


def _identity(path: Path) -> tuple[str, str, str]:
    name = path.name
    if name.endswith(".zip"):
        return "windows", "x86_64", "windows-portable"
    if name.endswith(".dmg"):
        return "macos", "arm64" if "arm64" in name else "x86_64", "macos-bundle"
    if name.endswith(".AppImage"):
        return "linux", "x86_64", "linux-appimage"
    if name.endswith(".deb"):
        return "linux", "x86_64", "linux-deb"
    return "linux", "x86_64", "linux-flatpak"


def build_metadata(release_dir: Path, version: str) -> dict:
    artifacts = []
    tag = f"v{version.lstrip('v')}"
    for path in sorted(release_dir.iterdir()):
        if not path.is_file() or not path.name.endswith(ASSET_SUFFIXES):
            continue
        platform, architecture, kind = _identity(path)
        artifacts.append({
            "platform": platform,
            "architecture": architecture,
            "kind": kind,
            "file": path.name,
            "size": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "url": f"https://github.com/mskomek/hpc-client-gui/releases/download/{tag}/{path.name}",
        })
    if not artifacts:
        raise RuntimeError("no update artifacts found")
    return {
        "schema_version": 1,
        "product": "hpc-client-gui",
        "version": version.lstrip("v"),
        "channel": "stable",
        "key_id": KEY_ID,
        "artifacts": artifacts,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release-dir", type=Path, required=True)
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    encoded_key = os.environ.get("UPDATE_SIGNING_PRIVATE_KEY_B64", "")
    if not encoded_key:
        raise RuntimeError("UPDATE_SIGNING_PRIVATE_KEY_B64 is required")
    private = Ed25519PrivateKey.from_private_bytes(base64.b64decode(encoded_key, validate=True))
    payload = json.dumps(build_metadata(args.release_dir, args.version), sort_keys=True, separators=(",", ":")).encode()
    envelope = {
        "schema": 1,
        "key_id": KEY_ID,
        "payload": base64.b64encode(payload).decode(),
        "signature": base64.b64encode(private.sign(payload)).decode(),
    }
    (args.release_dir / "UPDATE_METADATA.json").write_text(json.dumps(envelope, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Unprivileged PackageKit handoff for verified local DEB files."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PackageKitCapability:
    available: bool
    local_install: bool
    reason: str


def probe_packagekit(runner=subprocess.run) -> PackageKitCapability:
    try:
        result = runner(
            ["pkcon", "get-actions"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return PackageKitCapability(False, False, "PackageKit is unavailable.")
    actions = result.stdout or ""
    if result.returncode != 0:
        return PackageKitCapability(True, False, "PackageKit could not report supported actions.")
    if "install-local" not in actions:
        return PackageKitCapability(True, False, "PackageKit does not support local package installation.")
    return PackageKitCapability(True, True, "PackageKit local installation is available.")


def stage_verified_deb(source: Path, update_dir: Path) -> Path:
    """Copy verified bytes into a private, non-predictable staging directory."""
    if source.is_symlink():
        raise ValueError("verified update must be a regular DEB file")
    source = source.resolve(strict=True)
    if not source.is_file() or source.suffix.lower() != ".deb":
        raise ValueError("verified update must be a regular DEB file")
    update_dir.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix="deb-", dir=update_dir))
    target = staging / source.name
    try:
        with source.open("rb") as src, target.open("xb") as dst:
            os.chmod(target, 0o600)
            shutil.copyfileobj(src, dst, length=1024 * 1024)
            dst.flush()
            os.fsync(dst.fileno())
        return target
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def build_packagekit_command(deb_path: Path) -> list[str]:
    if deb_path.is_symlink():
        raise ValueError("package path must be a regular DEB file")
    path = deb_path.resolve()
    if path.suffix.lower() != ".deb" or not path.is_file():
        raise ValueError("package path must be a regular DEB file")
    return ["pkcon", "install-local", str(path)]

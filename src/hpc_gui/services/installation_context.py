"""Evidence-based installation detection for the updater."""

from __future__ import annotations

import os
import plistlib
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from hpc_gui.core.platform import current_architecture, current_os


@dataclass(frozen=True)
class InstallationContext:
    kind: str
    evidence: str
    executable: Path | None
    identity: str
    version: str
    architecture: str
    capability: str
    reason: str


def _executable() -> Path:
    return Path(sys.executable if getattr(sys, "frozen", False) else sys.argv[0]).resolve()


def _run(args: list[str]) -> str:
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return result.stdout[:4096].strip()


def _deb_context(executable: Path, architecture: str) -> InstallationContext | None:
    owner = _run(["dpkg-query", "-S", str(executable)])
    package = owner.split(":", 1)[0] if owner else ""
    if package != "hpc-client-gui":
        return None
    metadata = _run(["dpkg-query", "-W", "-f=${Package}\n${Version}\n${Architecture}", package])
    fields = metadata.splitlines()
    if len(fields) < 3 or fields[0] != package or fields[2] != "amd64":
        return InstallationContext(
            "deb", "dpkg-query", executable, package, fields[1] if len(fields) > 1 else "",
            architecture, "manual", "Package identity or architecture is not supported.",
        )
    return InstallationContext(
        "deb", "dpkg-query", executable, package, fields[1], architecture,
        "manual", "DEB updates require the Ubuntu/Debian installer wave.",
    )


def detect_installation() -> InstallationContext:
    os_key = current_os()
    architecture = current_architecture()
    executable = _executable()

    if os_key == "linux":
        if os.environ.get("FLATPAK_ID"):
            return InstallationContext("flatpak", "FLATPAK_ID", executable, os.environ["FLATPAK_ID"], "", architecture, "manual", "Updates are delegated to Flatpak.")
        appimage = os.environ.get("APPIMAGE")
        if appimage and Path(appimage).is_file() and Path(appimage).resolve() == executable:
            return InstallationContext("appimage", "APPIMAGE runtime", executable, "hpc-client-gui", "", architecture, "manual", "AppImage replacement is handled by a later update wave.")
        deb = _deb_context(executable, architecture)
        if deb:
            return deb
        return InstallationContext("source", "no package ownership evidence", executable, "hpc-client-gui", "", architecture, "manual", "This installation is not owned by a supported package manager.")

    if os_key == "macos":
        bundle = next((parent for parent in (executable, *executable.parents) if parent.suffix == ".app"), None)
        if bundle:
            info_path = bundle / "Contents" / "Info.plist"
            try:
                info = plistlib.loads(info_path.read_bytes())
            except (OSError, plistlib.InvalidFileException, ValueError):
                info = {}
            return InstallationContext("macos-bundle", "Info.plist", executable, str(info.get("CFBundleIdentifier") or ""), str(info.get("CFBundleShortVersionString") or ""), architecture, "manual", "Sparkle feasibility is required before automatic macOS updates.")

    if os_key == "windows" and getattr(sys, "frozen", False):
        return InstallationContext("windows", "frozen executable", executable, "hpc-client-gui", "", architecture, "windows", "Windows updater is supported.")
    return InstallationContext("unknown", "insufficient installation evidence", executable, "", "", architecture, "manual", "Installation type could not be identified safely.")

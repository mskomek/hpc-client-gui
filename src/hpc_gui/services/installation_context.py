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
            architecture, "unsupported", "Package identity or architecture is not supported.",
        )
    return InstallationContext(
        "deb", "dpkg-query", executable, package, fields[1], architecture,
        "linux-deb", "Updates are delegated to the system package manager.",
    )


def _flatpak_scope(app_id: str) -> str:
    for scope in ("user", "system"):
        if _run(["flatpak-spawn", "--host", "flatpak", "info", f"--{scope}", app_id]):
            return scope
    return "unknown"


def detect_installation() -> InstallationContext:
    os_key = current_os()
    architecture = current_architecture()
    executable = _executable()

    if os_key == "linux":
        if os.environ.get("FLATPAK_ID"):
            app_id = os.environ["FLATPAK_ID"]
            scope = _flatpak_scope(app_id)
            capability = "linux-flatpak" if app_id == "io.github.mskomek.HpcClientGui" and scope != "unknown" else "unsupported"
            return InstallationContext("flatpak", "FLATPAK_ID", executable, app_id, "", architecture, capability, f"Updates are delegated to Flatpak; scope={scope}")
        appimage = os.environ.get("APPIMAGE")
        appdir = os.environ.get("APPDIR")
        image = Path(appimage).resolve() if appimage else None
        runtime_matches = bool(
            image and image.is_file() and (
                image == executable
                or (appdir and Path(appdir).resolve() in executable.parents)
            )
        )
        if runtime_matches:
            capability = "linux-appimage" if os.access(image.parent, os.W_OK) else "unsupported"
            return InstallationContext("appimage", "APPIMAGE runtime", image, "hpc-client-gui", "", architecture, capability, "AppImage installation was identified safely." if capability == "linux-appimage" else "The AppImage directory is not writable.")
        deb = _deb_context(executable, architecture)
        if deb:
            return deb
        return InstallationContext("source", "no package ownership evidence", executable, "hpc-client-gui", "", architecture, "source", "Source installations require a manual update.")

    if os_key == "macos":
        bundle = next((parent for parent in (executable, *executable.parents) if parent.suffix == ".app"), None)
        if bundle:
            info_path = bundle / "Contents" / "Info.plist"
            try:
                info = plistlib.loads(info_path.read_bytes())
            except (OSError, plistlib.InvalidFileException, ValueError):
                info = {}
            identity = str(info.get("CFBundleIdentifier") or "")
            capability = "macos-bundle" if identity == "io.github.mskomek.HpcClientGui" and os.access(bundle.parent, os.W_OK) else "unsupported"
            return InstallationContext("macos-bundle", "Info.plist", executable, identity, str(info.get("CFBundleShortVersionString") or ""), architecture, capability, "Writable application bundle identified." if capability == "macos-bundle" else "Bundle identity or location is not supported.")

    if os_key == "windows" and getattr(sys, "frozen", False):
        return InstallationContext("windows", "frozen executable", executable, "hpc-client-gui", "", architecture, "windows-portable", "Windows portable updater is supported.")
    return InstallationContext("unknown", "insufficient installation evidence", executable, "", "", architecture, "unsupported", "Installation type could not be identified safely.")

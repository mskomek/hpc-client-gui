"""Shared Linux packaging base for HPC Client GUI.

This module is the single, testable source of truth for Linux release
packaging metadata and plan steps.  It never performs a real network or
package-manager operation; it resolves the version, inventories the required
release files, validates the AppImage definition files, and produces a
dry-run build plan that Wave 40 CI executes on the supported Linux baseline.

Run it directly for a dry-run plan (no build happens):

    python scripts/release_linux.py --version 1.2.4
    python scripts/release_linux.py --version 1.2.4 --json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
DIST_DIR = REPO_ROOT / "dist"
RELEASE_ROOT = DIST_DIR / "releases"
APPIMAGE_DEF_DIR = REPO_ROOT / "build" / "linux" / "appimage"
APPIMAGE_ICON = APPIMAGE_DEF_DIR / "hpc-client-gui.png"
DEB_DEF_DIR = REPO_ROOT / "build" / "linux" / "deb"
FLATPAK_DEF_DIR = REPO_ROOT / "build" / "linux" / "flatpak"
WINDOWS_ICON = REPO_ROOT / "build" / "windows" / "hpc-client-gui.ico"

DESKTOP_ENTRY_NAME = "hpc-client-gui.desktop"
APPRUN_NAME = "AppRun"
FLATPAK_ID = "io.github.mskomek.HpcClientGui"
REQUIRED_HELP_FILES = ("HELP_tr.md", "HELP_en.md", "CLI_GUIDE_tr.md", "CLI_GUIDE_en.md")
REQUIRED_LICENSE_FILES = ("LICENSE", "COMMERCIAL_LICENSE.md", "THIRD_PARTY_NOTICES.md", "QT_LGPL_SOURCE_OFFER.md")
THIRD_PARTY_LICENSES_DIR = REPO_ROOT / "third_party_licenses"


class PackagingError(RuntimeError):
    """An actionable Linux packaging failure."""


def require_ubuntu_host() -> None:
    """Require Ubuntu for artifact builds while keeping dry-run planning portable."""
    if sys.platform != "linux":
        raise PackagingError("Linux artifact builds require Ubuntu LTS (CI or WSL Ubuntu).")
    try:
        os_release = Path("/etc/os-release").read_text(encoding="utf-8")
    except OSError as exc:
        raise PackagingError("Linux artifact builds require an Ubuntu /etc/os-release file.") from exc
    distro_id = next(
        (line.partition("=")[2].strip().strip('"') for line in os_release.splitlines() if line.startswith("ID=")),
        "",
    )
    if distro_id != "ubuntu":
        raise PackagingError("Linux artifact builds require Ubuntu LTS (CI or WSL Ubuntu).")


def resolve_version() -> str:
    """Return the single authoritative release version or raise."""
    versions: List[str] = []

    pyproject = REPO_ROOT / "pyproject.toml"
    match = re.search(r'(?m)^version\s*=\s*"([^"]+)"\s*$', pyproject.read_text(encoding="utf-8"))
    if not match:
        raise PackagingError(f"pyproject.toml has no version declaration: {pyproject}")
    versions.append(match.group(1))

    init = SRC_DIR / "hpc_gui" / "__init__.py"
    match = re.search(r"__version__\s*=\s*'([^']+)'", init.read_text(encoding="utf-8"))
    if not match:
        raise PackagingError(f"__init__.py has no __version__ declaration: {init}")
    versions.append(match.group(1))

    cli = SRC_DIR / "hpc_gui" / "cli" / "main.py"
    match = re.search(r'CLI_VERSION\s*=\s*"([^"]+)"', cli.read_text(encoding="utf-8"))
    if not match:
        raise PackagingError(f"cli/main.py has no CLI_VERSION declaration: {cli}")
    versions.append(match.group(1))

    unique = set(versions)
    if len(unique) != 1:
        raise PackagingError(f"Version mismatch across sources: {', '.join(sorted(unique))}")
    return versions[0]


def appimage_artifact_name(version: str, arch: str = "x86_64") -> str:
    """Canonical AppImage artifact name, e.g. hpc-client-gui-1.2.4-x86_64.AppImage."""
    return f"hpc-client-gui-{version}-{arch}.AppImage"


def required_release_files() -> List[Path]:
    """Inventory of files every Linux release package must contain."""
    result: List[Path] = []
    docs_dir = SRC_DIR / "hpc_gui" / "docs"
    for name in REQUIRED_HELP_FILES:
        result.append(docs_dir / name)
    for name in REQUIRED_LICENSE_FILES:
        result.append(REPO_ROOT / name)
    result.append(REPO_ROOT / "third_party_licenses")
    return result


def validate_required_files() -> None:
    """Fail with an actionable message if any required release file is missing."""
    for path in required_release_files():
        if path.is_dir():
            if not any(path.iterdir()):
                raise PackagingError(f"Required third-party licenses dir is empty: {path}")
        elif not path.is_file():
            raise PackagingError(f"Required release file missing: {path}")


def validate_desktop_entry() -> None:
    """Validate the static AppImage .desktop entry without shipping bad metadata."""
    path = APPIMAGE_DEF_DIR / DESKTOP_ENTRY_NAME
    if not path.is_file():
        raise PackagingError(f"AppImage desktop entry missing: {path}")
    text = path.read_text(encoding="utf-8")
    if "[Desktop Entry]" not in text:
        raise PackagingError(f"AppImage desktop entry has no [Desktop Entry] section: {path}")
    if not re.search(r"(?m)^Exec=\S+$", text):
        raise PackagingError(f"AppImage desktop entry has no Exec= line: {path}")
    if not re.search(r"(?m)^Name=", text):
        raise PackagingError(f"AppImage desktop entry has no Name= line: {path}")


def validate_apprun() -> None:
    """Validate the AppImage AppRun launcher and require a shebang."""
    path = APPIMAGE_DEF_DIR / APPRUN_NAME
    if not path.is_file():
        raise PackagingError(f"AppImage AppRun launcher missing: {path}")
    text = path.read_text(encoding="utf-8")
    if not text.startswith("#!"):
        raise PackagingError(f"AppImage AppRun has no shebang: {path}")


def deb_artifact_name(version: str) -> str:
    """Canonical .deb artifact name, e.g. hpc-client-gui_1.2.4_amd64.deb."""
    return f"hpc-client-gui_{version}_amd64.deb"


def flatpak_artifact_name(version: str) -> str:
    """Canonical Flatpak bundle name, e.g. hpc-client-gui-1.2.4.flatpak."""
    return f"hpc-client-gui-{version}.flatpak"


def validate_deb_control() -> None:
    """Validate the .deb control file and require the version placeholder."""
    path = DEB_DEF_DIR / "DEBIAN" / "control"
    if not path.is_file():
        raise PackagingError(f".deb control file missing: {path}")
    text = path.read_text(encoding="utf-8")
    for field in ("Package:", "Version:", "Architecture:", "Description:"):
        if not re.search(rf"(?m)^{re.escape(field)}", text):
            raise PackagingError(f".deb control file has no {field} field: {path}")
    if "<VERSION>" not in text:
        raise PackagingError(f".deb control file has no <VERSION> placeholder: {path}")


def validate_flatpak_manifest() -> None:
    """Validate the Flatpak manifest parses and carries the required keys."""
    path = FLATPAK_DEF_DIR / f"{FLATPAK_ID}.json"
    if not path.is_file():
        raise PackagingError(f"Flatpak manifest missing: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PackagingError(f"Flatpak manifest is not valid JSON: {exc}") from exc
    for key in ("app-id", "runtime", "sdk", "command", "modules"):
        if key not in data:
            raise PackagingError(f"Flatpak manifest has no {key} key: {path}")
    if not isinstance(data.get("modules"), list) or not data["modules"]:
        raise PackagingError(f"Flatpak manifest modules must be a non-empty list: {path}")


def sha256_hex(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _tool(cmd: str) -> List[str]:
    return cmd.split()


def _pyinstaller_commands(version: str) -> List[List[str]]:
    return [
        ["python", "-m", "pip", "install", "--upgrade", "pyinstaller"],
        ["pyinstaller", "-y", "--clean", "build/linux/hpc-client-gui-linux.spec"],
    ]


def _appimage_assembly_commands(version: str) -> List[List[str]]:
    """Commands that assemble the AppDir and run appimagetool on Linux CI.

    These run in Wave 40 on the supported baseline; the plan and its inventory
    are validated here in a dry run.
    """
    artifact = appimage_artifact_name(version)
    return [
        ["mkdir", "-p", "dist/appimage/AppDir/usr/bin"],
        ["cp", "-a", "dist/hpc-client-gui/.", "dist/appimage/AppDir/usr/bin/"],
        ["cp", "build/linux/appimage/hpc-client-gui.desktop", "dist/appimage/AppDir/"],
        ["cp", "build/linux/appimage/AppRun", "dist/appimage/AppDir/AppRun"],
        ["chmod", "+x", "dist/appimage/AppDir/AppRun"],
        ["appimagetool", "dist/appimage/AppDir", f"dist/appimage/{artifact}"],
    ]


def _deb_commands(version: str) -> List[List[str]]:
    """Commands that build the .deb package on Linux CI (dry-run validated here)."""
    artifact = deb_artifact_name(version)
    control = DEB_DEF_DIR / "DEBIAN" / "control"
    return [
        [
            "bash",
            "-c",
            f"sed 's/<VERSION>/{version}/g' '{control}' > 'dist/deb/DEBIAN/control'",
        ],
        ["dpkg-deb", "--build", "dist/deb", f"dist/{artifact}"],
    ]


def _flatpak_commands(version: str) -> List[List[str]]:
    """Commands that build the Flatpak bundle on Linux CI (dry-run validated here)."""
    artifact = flatpak_artifact_name(version)
    manifest = FLATPAK_DEF_DIR / f"{FLATPAK_ID}.json"
    return [
        ["flatpak-builder", "--user", "--install-deps-from=flathub", "dist/flatpak/build", str(manifest)],
        ["flatpak", "build-bundle", "dist/flatpak/repo", f"dist/{artifact}", FLATPAK_ID],
    ]


def pip_install_command() -> List[str]:
    """The supported pip/source install path for Linux developers."""
    return ["python", "-m", "pip", "install", "-e", ".[test]"]


def validate_pip_metadata() -> None:
    """Verify the pip/source path is well-formed (pyproject entry point + deps)."""
    pyproject = REPO_ROOT / "pyproject.toml"
    if not pyproject.is_file():
        raise PackagingError(f"pyproject.toml missing: {pyproject}")
    text = pyproject.read_text(encoding="utf-8")
    if "requires-python" not in text:
        raise PackagingError("pyproject.toml has no requires-python declaration.")
    for dep in ("PySide6", "paramiko", "cryptography"):
        if dep not in text:
            raise PackagingError(f"pyproject.toml missing dependency {dep}.")
    entry = SRC_DIR / "hpc_gui" / "__main__.py"
    if not entry.is_file():
        raise PackagingError(f"pip entry point missing: {entry}")


def release_dir_contents(version: str) -> List[str]:
    """Expected files under dist/releases/v<version>/ for the Linux release."""
    return [
        appimage_artifact_name(version),
        f"{appimage_artifact_name(version)}.sha256",
        deb_artifact_name(version),
        f"{deb_artifact_name(version)}.sha256",
        flatpak_artifact_name(version),
        f"{flatpak_artifact_name(version)}.sha256",
    ]


def _run(command: List[str], *, cwd: Path = REPO_ROOT) -> None:
    """Run a visible packaging command and preserve actionable diagnostics."""
    print("+", " ".join(command))
    result = subprocess.run(command, cwd=str(cwd), text=True)
    if result.returncode != 0:
        raise PackagingError(f"Command failed with exit {result.returncode}: {' '.join(command)}")


def _generate_version_manifest(version: str) -> None:
    _run([sys.executable, "scripts/generate_third_party_versions.py", "--version", version])
    _run([sys.executable, "scripts/generate_sbom.py", "--version", version])


def _copy_tree(source: Path, destination: Path) -> None:
    if not source.is_dir():
        raise PackagingError(f"Packaging input directory missing: {source}")
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)


def _stage_common_release_files(destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for path in required_release_files():
        target = destination / path.name
        if path.is_dir():
            _copy_tree(path, target)
        else:
            shutil.copy2(path, target)
    shutil.copy2(REPO_ROOT / "THIRD_PARTY_VERSIONS.txt", destination / "THIRD_PARTY_VERSIONS.txt")
    shutil.copy2(REPO_ROOT / "SBOM.cdx.json", destination / "SBOM.cdx.json")
    help_dir = destination / "help"
    help_dir.mkdir(exist_ok=True)
    docs_dir = SRC_DIR / "hpc_gui" / "docs"
    for name in REQUIRED_HELP_FILES:
        shutil.copy2(docs_dir / name, help_dir / name)


def _build_appimage(version: str, output_dir: Path) -> Path:
    appimagetool = os.environ.get("APPIMAGETOOL") or shutil.which("appimagetool")
    if not appimagetool:
        raise PackagingError("appimagetool is required; set APPIMAGETOOL to a pinned executable.")
    app_dir = DIST_DIR / "appimage" / "AppDir"
    if app_dir.parent.exists():
        shutil.rmtree(app_dir.parent)
    (app_dir / "usr" / "bin").mkdir(parents=True)
    _copy_tree(DIST_DIR / "hpc-client-gui", app_dir / "usr" / "bin")
    shutil.copy2(APPIMAGE_DEF_DIR / DESKTOP_ENTRY_NAME, app_dir / DESKTOP_ENTRY_NAME)
    if APPIMAGE_ICON.is_file():
        shutil.copy2(APPIMAGE_ICON, app_dir / APPIMAGE_ICON.name)
    shutil.copy2(APPIMAGE_DEF_DIR / APPRUN_NAME, app_dir / APPRUN_NAME)
    os.chmod(app_dir / APPRUN_NAME, 0o755)
    artifact = output_dir / appimage_artifact_name(version)
    _run([appimagetool, str(app_dir), str(artifact)])
    return artifact


def _build_deb(version: str, output_dir: Path) -> Path:
    staging = DIST_DIR / "deb"
    if staging.exists():
        shutil.rmtree(staging)
    (staging / "DEBIAN").mkdir(parents=True)
    (staging / "usr" / "lib").mkdir(parents=True)
    (staging / "usr" / "bin").mkdir(parents=True)
    (staging / "usr" / "share" / "applications").mkdir(parents=True)
    control = (DEB_DEF_DIR / "DEBIAN" / "control").read_text(encoding="utf-8")
    (staging / "DEBIAN" / "control").write_text(control.replace("<VERSION>", version), encoding="utf-8")
    _copy_tree(DIST_DIR / "hpc-client-gui", staging / "usr" / "lib" / "hpc-client-gui")
    launcher = "#!/bin/sh\nexec /usr/lib/hpc-client-gui/hpc-client-gui \"$@\"\n"
    launcher_path = staging / "usr" / "bin" / "hpc-client-gui"
    launcher_path.write_text(launcher, encoding="utf-8")
    os.chmod(launcher_path, 0o755)
    shutil.copy2(APPIMAGE_DEF_DIR / DESKTOP_ENTRY_NAME, staging / "usr" / "share" / "applications" / DESKTOP_ENTRY_NAME)
    _stage_common_release_files(staging / "usr" / "share" / "doc" / "hpc-client-gui")
    artifact = output_dir / deb_artifact_name(version)
    _run(["dpkg-deb", "--build", str(staging), str(artifact)])
    return artifact


def _build_flatpak(version: str, output_dir: Path) -> Path:
    flatpak_builder = shutil.which("flatpak-builder")
    flatpak = shutil.which("flatpak")
    if not flatpak_builder or not flatpak:
        raise PackagingError("flatpak-builder and flatpak are required for the Flatpak artifact.")
    manifest = FLATPAK_DEF_DIR / f"{FLATPAK_ID}.json"
    repo = DIST_DIR / "flatpak" / "repo"
    build_dir = DIST_DIR / "flatpak" / "build"
    if build_dir.exists():
        shutil.rmtree(build_dir)
    repo.mkdir(parents=True, exist_ok=True)
    _run([flatpak_builder, "--force-clean", "--repo", str(repo), str(build_dir), str(manifest)])
    artifact = output_dir / flatpak_artifact_name(version)
    _run([flatpak, "build-bundle", str(repo), str(artifact), FLATPAK_ID])
    return artifact


def execute_linux_build(version: Optional[str] = None) -> List[Path]:
    """Build all approved Linux artifacts and stage checksums and metadata."""
    require_ubuntu_host()
    effective_version = version or resolve_version()
    if effective_version != resolve_version():
        raise PackagingError(f"Requested version does not match source version: {effective_version}")
    _generate_version_manifest(effective_version)
    if not (REPO_ROOT / "THIRD_PARTY_VERSIONS.txt").is_file():
        raise PackagingError("Version manifest generation produced no THIRD_PARTY_VERSIONS.txt")
    validate_required_files()
    validate_desktop_entry()
    validate_apprun()
    validate_deb_control()
    validate_flatpak_manifest()
    validate_pip_metadata()
    _run(["pyinstaller", "-y", "--clean", "build/linux/hpc-client-gui-linux.spec"])
    release_dir = RELEASE_ROOT / f"v{effective_version}"
    if release_dir.exists():
        raise PackagingError(f"Refusing to overwrite existing release directory: {release_dir}")
    release_dir.mkdir(parents=True)
    artifacts = [
        _build_appimage(effective_version, release_dir),
        _build_deb(effective_version, release_dir),
        _build_flatpak(effective_version, release_dir),
    ]
    _stage_common_release_files(release_dir)
    for artifact in artifacts:
        digest = sha256_hex(artifact)
        (release_dir / f"{artifact.name}.sha256").write_text(f"{digest}  {artifact.name}\n", encoding="ascii")
    return artifacts


@dataclass
class BuildPlan:
    version: str
    stages: List[dict] = field(default_factory=list)


def build_linux_plan(version: Optional[str] = None) -> BuildPlan:
    """Return a dry-run build plan for all approved Linux formats.

    No build, network, or package-manager operation is performed.
    """
    effective_version = version or resolve_version()
    if not re.match(r"^\d+\.\d+\.\d+$", effective_version):
        raise PackagingError(f"Version must be X.Y.Z, got: {effective_version}")

    validate_required_files()
    validate_desktop_entry()
    validate_apprun()
    validate_deb_control()
    validate_flatpak_manifest()
    validate_pip_metadata()

    plan = BuildPlan(version=effective_version)
    plan.stages.append({"name": "validate-version", "detail": effective_version})
    plan.stages.append({"name": "validate-required-files", "detail": len(required_release_files())})
    plan.stages.append({"name": "validate-pip-source", "detail": " ".join(pip_install_command())})
    plan.stages.append({"name": "install-deps", "commands": _pyinstaller_commands(effective_version)})
    plan.stages.append(
        {
            "name": "assemble-appimage",
            "artifact": appimage_artifact_name(effective_version),
            "commands": _appimage_assembly_commands(effective_version),
        }
    )
    plan.stages.append(
        {
            "name": "build-deb",
            "artifact": deb_artifact_name(effective_version),
            "commands": _deb_commands(effective_version),
        }
    )
    plan.stages.append(
        {
            "name": "build-flatpak",
            "artifact": flatpak_artifact_name(effective_version),
            "commands": _flatpak_commands(effective_version),
        }
    )
    plan.stages.append(
        {
            "name": "checksum",
            "artifacts": [
                appimage_artifact_name(effective_version),
                deb_artifact_name(effective_version),
                flatpak_artifact_name(effective_version),
            ],
            "detail": "sha256 files written next to each artifact in dist/releases/v<version>/",
        }
    )
    plan.stages.append(
        {
            "name": "release-layout",
            "dir": f"dist/releases/v{effective_version}",
            "expected": release_dir_contents(effective_version),
            "detail": "each artifact and its .sha256 must be present; existing version folders are never overwritten",
        }
    )
    return plan


def plan_to_dict(plan: BuildPlan) -> dict:
    return {
        "version": plan.version,
        "artifacts": [
            appimage_artifact_name(plan.version),
            deb_artifact_name(plan.version),
            flatpak_artifact_name(plan.version),
        ],
        "stages": plan.stages,
    }


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="release_linux", description="Linux packaging plan (dry-run).")
    parser.add_argument("--version", help="Override the version (default: resolve from sources).")
    parser.add_argument("--json", action="store_true", help="Emit the plan as JSON.")
    parser.add_argument("--execute", action="store_true", help="Build and stage all Linux artifacts.")
    args = parser.parse_args(argv)

    try:
        if args.execute:
            artifacts = execute_linux_build(args.version)
            print("Linux artifacts:")
            for artifact in artifacts:
                print(f" - {artifact}")
            return 0
        plan = build_linux_plan(args.version)
    except PackagingError as exc:
        print(f"release_linux: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(plan_to_dict(plan), indent=2, ensure_ascii=False))
    else:
        print(f"Linux release plan v{plan.version}")
        print(f"Artifacts: {', '.join(plan_to_dict(plan)['artifacts'])}")
        for stage in plan.stages:
            print(f" - {stage['name']}: {stage.get('detail', '')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

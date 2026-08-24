"""Plan and execute the macOS DMG release pipeline.

Dry-run planning is portable; ``--execute`` is deliberately macOS-only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import plistlib
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DIST_ROOT = REPO_ROOT / "dist"
RELEASE_ROOT = DIST_ROOT / "releases"
SPEC_PATH = REPO_ROOT / "build" / "macos" / "hpc-client-gui.spec"
SMOKE_SCRIPT = REPO_ROOT / "scripts" / "macos_release_smoke.py"


class PackagingError(RuntimeError):
    pass


def resolve_version() -> str:
    from release_linux import resolve_version as _resolve_version

    return _resolve_version()


def artifact_name(version: str, arch: str) -> str:
    if arch not in {"arm64", "x86_64"}:
        raise PackagingError("architecture must be arm64 or x86_64")
    return f"hpc-client-gui_macos_{arch}.dmg"


def require_macos() -> None:
    if sys.platform != "darwin":
        raise PackagingError("macOS artifact execution requires Darwin")


def require_native_arch(arch: str) -> None:
    actual = platform.machine().lower()
    normalized = "arm64" if actual in {"arm64", "aarch64"} else "x86_64" if actual in {"x86_64", "amd64"} else actual
    if normalized != arch:
        raise PackagingError(f"requested {arch}, but runner architecture is {normalized}")


@dataclass(frozen=True)
class ReleasePlan:
    version: str
    arch: str
    artifact: str
    output: Path
    staging: Path
    commands: tuple[tuple[str, ...], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "version": self.version,
            "arch": self.arch,
            "artifact": self.artifact,
            "output": str(self.output),
            "staging": str(self.staging),
            "commands": [list(command) for command in self.commands],
        }


def make_plan(version: str, arch: str) -> ReleasePlan:
    if version != resolve_version():
        raise PackagingError(f"requested version {version} does not match repository version")
    if not SPEC_PATH.is_file():
        raise PackagingError(f"macOS PyInstaller spec missing: {SPEC_PATH}")
    artifact = artifact_name(version, arch)
    release_dir = RELEASE_ROOT / f"v{version}"
    staging = release_dir / f"macos_{arch}" / "dmg-root"
    output = release_dir / artifact
    commands = (
        (sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", str(SPEC_PATH)),
        ("hdiutil", "create", "-format", "UDZO", "-srcfolder", str(staging), str(output)),
        ("hdiutil", "verify", str(output)),
    )
    return ReleasePlan(version, arch, artifact, output, staging, commands)


def _run(command: tuple[str, ...], *, env: dict[str, str] | None = None) -> None:
    result = subprocess.run(command, cwd=REPO_ROOT, env=env, text=True)
    if result.returncode:
        raise PackagingError(f"command failed ({result.returncode}): {' '.join(command)}")


def _validate_bundle(app: Path, version: str) -> None:
    if not app.is_dir() or app.suffix != ".app":
        raise PackagingError(f"PyInstaller app bundle missing: {app}")
    info_path = app / "Contents" / "Info.plist"
    if not info_path.is_file():
        raise PackagingError(f"bundle Info.plist missing: {info_path}")
    try:
        info = plistlib.loads(info_path.read_bytes())
    except (OSError, plistlib.InvalidFileException) as exc:
        raise PackagingError(f"invalid bundle Info.plist: {info_path}") from exc
    if info.get("CFBundleIdentifier") != "io.github.mskomek.HpcClientGui":
        raise PackagingError("bundle identifier mismatch")
    if str(info.get("CFBundleShortVersionString")) != version:
        raise PackagingError("bundle version mismatch")
    forbidden = {"vcxsrv.exe", "plink.exe"}
    for path in app.rglob("*"):
        if path.name.lower() in forbidden or path.suffix.lower() == ".dll":
            raise PackagingError(f"Windows payload found in Mac app: {path}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def execute(plan: ReleasePlan) -> Path:
    require_macos()
    require_native_arch(plan.arch)
    env = dict(os.environ, MACOS_TARGET_ARCH=plan.arch, APP_VERSION=plan.version)
    _run(plan.commands[0], env=env)
    app = DIST_ROOT / "HPC Client GUI.app"
    _validate_bundle(app, plan.version)
    _run((sys.executable, str(SMOKE_SCRIPT), "--app", str(app), "--version", plan.version, "--gui"), env=env)

    if plan.staging.exists():
        shutil.rmtree(plan.staging)
    plan.staging.mkdir(parents=True)
    shutil.copytree(app, plan.staging / app.name)
    (plan.staging / "Applications").symlink_to("/Applications")
    plan.output.parent.mkdir(parents=True, exist_ok=True)
    _run(plan.commands[1])
    _run(plan.commands[2])
    checksum = plan.output.with_name(plan.output.name + ".sha256")
    checksum.write_text(f"{_sha256(plan.output)}  {plan.output.name}\n", encoding="ascii")
    return plan.output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="release_macos")
    parser.add_argument("--version", required=True)
    parser.add_argument("--arch", choices=("arm64", "x86_64"), required=True)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    try:
        plan = make_plan(args.version, args.arch)
        if args.execute:
            output = execute(plan)
            payload = {**plan.to_dict(), "output": str(output)}
        else:
            payload = plan.to_dict()
        print(json.dumps(payload, ensure_ascii=False, indent=2) if args.json else f"macOS release {'built' if args.execute else 'plan'}: {plan.artifact}")
        return 0
    except PackagingError as exc:
        print(f"release_macos: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

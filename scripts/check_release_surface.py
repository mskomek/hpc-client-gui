"""Validate README release links, public copy, and package naming contracts."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


VERSION_RE = re.compile(r'(?m)^version\s*=\s*"([^"\n]+)"\s*$')
TAG_LINK_RE = re.compile(r"https://github\.com/[^\s)]+/releases/tag/v\d+")
PATCH_RELEASE_RE = re.compile(r"https://github\.com/[^\s)]+/releases/(?:tag/)?v\d+")
RESIDUE_RE = re.compile(r"(?i)drafted later|this wave|agent-runs|deepseek|opencode|waves/")


def check_release_surface(root: Path) -> list[str]:
    problems: list[str] = []
    if (root / ".git").exists():
        tracked_dist = subprocess.run(
            ["git", "ls-files", "dist/releases"],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
        if tracked_dist:
            problems.append(
                "dist/releases: generated release artifacts must not be tracked "
                f"({len(tracked_dist)} paths; remove them from the current tree)"
            )
    readme = (root / "README.md").read_text(encoding="utf-8")
    version_match = VERSION_RE.search((root / "pyproject.toml").read_text(encoding="utf-8"))
    if not version_match:
        return ["pyproject.toml: version declaration not found"]

    if TAG_LINK_RE.search(readme) or PATCH_RELEASE_RE.search(readme):
        problems.append("README.md: release links must use stable latest routes, not versioned URLs")
    if "releases/latest" not in readme:
        problems.append("README.md: no stable latest release link")
    for match in RESIDUE_RE.finditer(readme):
        line = readme.count("\n", 0, match.start()) + 1
        problems.append(f"README.md:{line}: internal release/process residue {match.group(0)!r}")

    for phrase in ("Windows", "Linux", "GUI", "CLI", "SSH", "SFTP", "Slurm"):
        if phrase not in readme:
            problems.append(f"README.md: required product phrase missing: {phrase}")

    release_script = (root / "scripts" / "release.ps1").read_text(encoding="utf-8")
    if 'hpc-client-gui_windows_onedir.zip' not in release_script:
        problems.append("scripts/release.ps1: Windows portable ZIP name is missing")
    linux_script = (root / "scripts" / "release_linux.py").read_text(encoding="utf-8")
    for artifact in (
        'f"hpc-client-gui-{version}-{arch}.AppImage"',
        'f"hpc-client-gui_{version}_amd64.deb"',
        'f"hpc-client-gui-{version}.flatpak"',
    ):
        if artifact not in linux_script:
            problems.append(f"scripts/release_linux.py: Linux artifact naming contract is missing: {artifact}")
    workflow = (root / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    if "dist/releases/v${{ github.event.inputs.version }}/" not in workflow:
        problems.append(".github/workflows/release.yml: canonical release directory is missing")
    return problems


def main(argv: list[str] | None = None) -> int:
    root = Path((argv or sys.argv[1:])[0]) if (argv or sys.argv[1:]) else Path(__file__).resolve().parents[1]
    problems = check_release_surface(root)
    if problems:
        print(f"release surface check: FAILED ({len(problems)})")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print("release surface check: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

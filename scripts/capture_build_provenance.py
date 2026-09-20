"""Pre-build provenance capture and stale-output guard (W14 / HPC-W04-PROV-001..003).

Workstream A requires, before every build:

1. recording ``git status --short`` and ``git rev-parse HEAD`` for the
   candidate source (main and plugin repositories);
2. recording dependency/toolchain versions relevant to packaging;
3. never reusing an unidentified executable -- old outputs must be cleaned
   or explicitly archived outside the candidate path.

``capture_provenance`` implements (1) and (2); ``guard_candidate_dir``
implements (3) across independent roots (the candidate directory itself,
``dist/`` and ``build/``) so a stale executable cannot be mistaken for the
fresh candidate.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Executable-ish suffixes that must never be silently reused.
STALE_EXECUTABLE_SUFFIXES = (".exe", ".msi", ".whl", ".zip", ".tar.gz", ".dmg", ".deb", ".AppImage", ".flatpak")

# Roots inspected for stale outputs, relative to the repository root.
STALE_SEARCH_ROOTS = ("dist", "build")

UNKNOWN = "unknown"


def _run_git(args: list[str], cwd: Path) -> str | None:
    try:
        proc = subprocess.run(
            ["git", *args], cwd=cwd, capture_output=True, text=True, check=False, timeout=15
        )
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip()


def _valid_sha(value: str | None) -> str:
    if value and len(value) == 40 and all(c in "0123456789abcdefABCDEF" for c in value):
        return value
    return UNKNOWN


def _plugin_root() -> Path | None:
    sibling = ROOT.parent / "hpc-client-gui-plugins"
    if (sibling / ".git").exists():
        return sibling
    return None


def _toolchain_versions() -> dict[str, str]:
    versions: dict[str, str] = {"python": platform.python_version()}
    for dist_name, key in (("pyinstaller", "pyinstaller"), ("pip", "pip"), ("setuptools", "setuptools")):
        try:
            from importlib import metadata as _metadata

            versions[key] = _metadata.version(dist_name)
        except Exception:
            versions[key] = UNKNOWN
    versions["os_arch"] = f"{platform.system().lower()}/{platform.machine().lower()}"
    return versions


def capture_provenance(root: Path = ROOT) -> dict:
    """Record clean-provenance facts for the candidate source tree."""
    main_status = _run_git(["status", "--short"], root)
    main_head = _valid_sha(_run_git(["rev-parse", "HEAD"], root))
    plugin_head = UNKNOWN
    plugin_status: str | None = None
    plugin_root = _plugin_root()
    if plugin_root is not None:
        plugin_head = _valid_sha(_run_git(["rev-parse", "HEAD"], plugin_root))
        plugin_status = _run_git(["status", "--short"], plugin_root)
    try:
        lock_ref = hashlib.sha256((root / "requirements-release.lock").read_bytes()).hexdigest()
    except OSError:
        lock_ref = UNKNOWN
    return {
        "main_commit": main_head,
        "main_status": main_status if main_status is not None else UNKNOWN,
        "main_dirty": bool(main_status) if main_status not in (None, UNKNOWN) else None,
        "plugin_commit": plugin_head,
        "plugin_status": plugin_status if plugin_status is not None else UNKNOWN,
        "toolchain": _toolchain_versions(),
        "dependency_lock_sha256": lock_ref,
        "captured_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }


def _is_executable_artifact(path: Path) -> bool:
    name = path.name.lower()
    return any(name.endswith(suffix.lower()) for suffix in STALE_EXECUTABLE_SUFFIXES)


def find_stale_executables(
    candidate_dir: Path,
    search_roots: tuple[str, ...] | None = None,
    known_fresh: frozenset[str] | set[str] | None = None,
) -> list[Path]:
    """List unidentified executables that could be confused with the candidate.

    A stale executable is any executable-ish file under the candidate
    directory or the independent ``dist/`` / ``build/`` roots that is not
    the declared candidate artifact itself.  The candidate directory may
    not exist yet (fresh build) -- then only the independent roots apply.
    ``search_roots`` overrides the independent roots (relative to the
    repository root); pass ``()`` to inspect only the candidate directory.
    ``known_fresh`` names files inside ``candidate_dir`` that were produced
    by the current build and must not be mistaken for stale outputs.
    """
    stale: list[Path] = []
    candidate_exists = candidate_dir.exists()
    roots = [candidate_dir] if candidate_exists else []
    for rel in STALE_SEARCH_ROOTS if search_roots is None else search_roots:
        root = ROOT / rel
        if not root.exists():
            continue
        if candidate_exists and root.resolve() == candidate_dir.resolve():
            continue
        roots.append(root)
    seen: set[Path] = set()
    fresh = set(known_fresh or ())
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file() or not _is_executable_artifact(path):
                continue
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            if candidate_exists and root.resolve() == candidate_dir.resolve() and path.name in fresh:
                continue
            stale.append(path)
    return stale


def guard_candidate_dir(
    candidate_dir: Path,
    archive_outside: Path | None = None,
    search_roots: tuple[str, ...] | None = None,
    known_fresh: frozenset[str] | set[str] | None = None,
) -> list[Path]:
    """Enforce the stale-dist guard for a build candidate directory.

    Returns the quarantined paths.  When ``archive_outside`` is given, stale
    outputs are moved to an explicitly named archive outside the candidate
    path; otherwise a ``ValueError`` is raised listing the stale files so the
    caller must clean or archive them before building.
    """
    stale = find_stale_executables(candidate_dir, search_roots, known_fresh)
    if not stale:
        return []
    if archive_outside is None:
        listing = "\n".join(f"  - {path}" for path in stale)
        raise ValueError(
            "stale build outputs could be confused with the candidate; "
            f"clean or archive them outside {candidate_dir}:\n{listing}"
        )
    archive_outside.mkdir(parents=True, exist_ok=True)
    if candidate_dir.exists() and archive_outside.resolve().is_relative_to(candidate_dir.resolve()):
        raise ValueError("archive directory must be outside the candidate path")
    moved: list[Path] = []
    for path in stale:
        try:
            target = archive_outside / path.name
            shutil.move(str(path), str(target))
            moved.append(target)
        except OSError as exc:
            raise ValueError(f"cannot quarantine stale output {path}: {exc}") from exc
    return moved


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-dir", type=Path, default=None)
    parser.add_argument("--archive-outside", type=Path, default=None)
    parser.add_argument(
        "--known-fresh",
        action="append",
        default=None,
        help="file name inside the candidate dir produced by the current build; "
        "repeatable; exempt from the stale listing (post-build re-verification)",
    )
    parser.add_argument("--json", action="store_true", help="print captured provenance as JSON")
    args = parser.parse_args(argv)

    provenance = capture_provenance(ROOT)
    if args.json or args.candidate_dir is None:
        print(json.dumps(provenance, indent=2))
    if args.candidate_dir is not None:
        try:
            moved = guard_candidate_dir(
                args.candidate_dir.resolve(),
                args.archive_outside,
                known_fresh=set(args.known_fresh or ()),
            )
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        if moved:
            print(f"quarantined {len(moved)} stale output(s) outside the candidate path")
            for path in moved:
                print(f"  - {path}")
        else:
            print(f"candidate clean: {args.candidate_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

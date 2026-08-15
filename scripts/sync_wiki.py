"""Mirror `docs/wiki/` to the GitHub wiki repository.

Dry-run by default: prints the exact add/update/delete plan and writes nothing.
Publication requires an explicit `--publish` and a clean `check_wiki.py` run.

    python scripts/sync_wiki.py              # plan only
    python scripts/sync_wiki.py --publish    # clone, mirror, commit, push
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import check_wiki

REPO_ROOT = Path(__file__).resolve().parents[1]
WIKI_SOURCE = REPO_ROOT / "docs" / "wiki"
WIKI_REMOTE = "https://github.com/mskomek/hpc-client-gui.wiki.git"
# Never mirrored, whatever ends up inside docs/wiki/.
EXCLUDED_NAMES = {"README.md"}
EXCLUDED_PATTERN = re.compile(
    r"(^|[\\/])(waves|\.agent-runs|\.git|\.env)([\\/]|$)"
    r"|\.(pem|key|ppk|p12|pfx)$"
    r"|(^|[\\/])(id_rsa|id_ed25519|known_hosts|credentials|secrets)",
    re.IGNORECASE,
)


def _run(args: list[str], cwd: Path | None = None) -> str:
    result = subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def collect_source_files() -> list[Path]:
    """Files to mirror, as paths relative to `docs/wiki/`."""
    files: list[Path] = []
    for path in sorted(WIKI_SOURCE.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(WIKI_SOURCE)
        if rel.name in EXCLUDED_NAMES:
            continue
        if EXCLUDED_PATTERN.search(str(rel)):
            raise SystemExit(f"refusing to mirror excluded path: {rel}")
        files.append(rel)
    return files


def build_plan(source: list[Path], target_root: Path) -> dict[str, list[Path]]:
    existing = {
        p.relative_to(target_root)
        for p in target_root.rglob("*")
        if p.is_file() and ".git" not in p.parts
    }
    add, update = [], []
    for rel in source:
        target = target_root / rel
        if rel not in existing:
            add.append(rel)
        elif target.read_bytes() != (WIKI_SOURCE / rel).read_bytes():
            update.append(rel)
    delete = sorted(existing - set(source))
    return {"add": add, "update": update, "delete": delete}


def print_plan(plan: dict[str, list[Path]]) -> None:
    for action in ("add", "update", "delete"):
        entries = plan[action]
        print(f"{action} ({len(entries)}):")
        for rel in entries:
            print(f"  {action[0].upper()} {rel.as_posix()}")


def apply_plan(plan: dict[str, list[Path]], target_root: Path) -> None:
    for rel in plan["delete"]:
        (target_root / rel).unlink()
    for rel in plan["add"] + plan["update"]:
        target = target_root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(WIKI_SOURCE / rel, target)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--publish", action="store_true", help="Commit and push the mirrored wiki.")
    parser.add_argument("--remote", default=WIKI_REMOTE, help="Wiki repository URL.")
    args = parser.parse_args(argv)

    problems = check_wiki.check_wiki(WIKI_SOURCE)
    if problems:
        print("refusing to sync: check_wiki.py reports problems")
        for item in problems:
            print("  -", item)
        return 1

    source = collect_source_files()
    with tempfile.TemporaryDirectory() as tmp:
        target_root = Path(tmp) / "wiki"
        print(f"cloning {args.remote}")
        _run(["git", "clone", "--depth", "1", args.remote, str(target_root)])
        plan = build_plan(source, target_root)
        print_plan(plan)

        if not args.publish:
            print("\ndry run: nothing was written. Re-run with --publish to apply.")
            return 0
        if not any(plan.values()):
            print("\nnothing to publish.")
            return 0

        apply_plan(plan, target_root)
        _run(["git", "add", "-A"], cwd=target_root)
        _run(["git", "commit", "-m", "docs: sync wiki from docs/wiki/"], cwd=target_root)
        _run(["git", "push", "origin", "HEAD"], cwd=target_root)
        print("\npublished.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

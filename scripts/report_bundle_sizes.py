"""Report the largest bundled files and frameworks of a PyInstaller bundle.

The macOS DMG budget work needs evidence, not guesses: this script walks a
bundle directory (for example ``dist/HPC Client GUI.app`` or the COLLECT
output directory), aggregates sizes per top-level framework/directory plus
per file, and writes a sorted report so unused payloads can be identified
and safe exclusions justified.

Usage:
    python scripts/report_bundle_sizes.py --bundle "dist/HPC Client GUI.app" \
        --output dist/releases/v1.5.1/bundle-size-report-macos-arm64.txt
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

TOP_N = 40


def _iter_files(root: Path):
    for path in sorted(root.rglob("*")):
        if path.is_file() and not path.is_symlink():
            yield path


def collect_report(bundle: Path) -> dict[str, object]:
    if not bundle.is_dir():
        raise FileNotFoundError(f"bundle directory does not exist: {bundle}")

    files: list[tuple[int, str]] = []
    groups: dict[str, int] = {}
    total = 0
    for path in _iter_files(bundle):
        size = path.stat().st_size
        total += size
        files.append((size, str(path.relative_to(bundle))))
        relative = path.relative_to(bundle)
        group_parts = [part for part in relative.parts[:3] if part != "Contents"]
        group = "/".join(group_parts[:2]) or "(root)"
        groups[group] = groups.get(group, 0) + size

    files.sort(reverse=True)
    return {
        "bundle": str(bundle),
        "total_bytes": total,
        "file_count": len(files),
        "largest_files": files[:TOP_N],
        "largest_groups": sorted(groups.items(), key=lambda item: item[1], reverse=True)[:TOP_N],
    }


def format_report(report: dict[str, object]) -> str:
    lines = [
        f"Bundle: {report['bundle']}",
        f"Total bytes: {report['total_bytes']}",
        f"File count: {report['file_count']}",
        "",
        f"Top {len(report['largest_groups'])} bundled groups by size:",
    ]
    for name, size in report["largest_groups"]:
        lines.append(f"{size:>14,d}  {name}")
    lines.append("")
    lines.append(f"Top {len(report['largest_files'])} bundled files by size:")
    for size, name in report["largest_files"]:
        lines.append(f"{size:>14,d}  {name}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)

    try:
        report = collect_report(args.bundle)
    except FileNotFoundError as exc:
        print(f"report_bundle_sizes: {exc}", file=sys.stderr)
        return 2

    text = format_report(report)
    print(text)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

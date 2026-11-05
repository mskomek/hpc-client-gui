"""CLI adapter used by the HPC Client GUI openfoam namespace."""
from __future__ import annotations

import argparse
from pathlib import Path

from .api import lint_paths
from hpc_gui.openfoam_core.release_support import supported_releases


def add_parser(commands) -> None:
    group = commands.add_parser("openfoam", help="OpenFOAM.com / ESI tools")
    sub = group.add_subparsers(dest="openfoam_command", required=True)
    lint = sub.add_parser("lint", help="Run read-only static lint on dictionaries or case roots")
    lint.add_argument("paths", nargs="+", type=Path)
    lint.add_argument("--release", choices=supported_releases(), default="v2312")
    lint.add_argument("--format", choices=("text", "json", "markdown"), default="text")
    lint.add_argument("--output", type=Path, help="Write the selected report format to this file")
    lint.set_defaults(handler=run_lint)


def run_lint(args: argparse.Namespace) -> int:
    result = lint_paths(args.paths, release=args.release)
    if args.format == "json":
        output = result.to_json()
    elif args.format == "markdown":
        output = result.to_markdown()
    else:
        output = "\n".join(
            f"{d.verification_level.upper()} {d.severity.upper()} {d.rule_id} {d.path}:{d.line}:{d.column}: {d.message}"
            for d in result.diagnostics
        ) or "No findings from enabled static rules."
        output = f"OpenFOAM.com / ESI {result.version}\n{output}"
    if args.output:
        args.output.write_text(output, encoding="utf-8")
    else:
        print(output)
    return 1 if result.errors else 0

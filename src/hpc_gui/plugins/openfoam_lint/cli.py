"""Standalone OpenFOAM Linter CLI (W65 LINT-013, G38).

Works with the Studio plugin uninstalled/disabled: imports only
``openfoam_lint`` engine modules. JSON stdout carries the same rule IDs,
severities and file/line/column anchors as the GUI path. Exit codes:
0 = no error-or-higher findings, 1 = errors found, 2 = usage/IO error.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _lint_paths(paths: list[str], *, release: str = "v2312") -> list[dict]:
    from hpc_gui.plugins.openfoam_lint import api
    diagnostics = []
    for raw in paths:
        path = Path(raw).expanduser()
        if not path.exists() and not path.is_symlink():
            raise ValueError(f"selected path does not exist: {path}")
        # Use the canonical bounded, link-rejecting scanner. A CLI path is
        # a filesystem selector, never an untrusted lint_text file_name.
        for diag in api.lint_paths([path], release=release):
            diagnostics.append({"rule": diag.rule, "severity": diag.severity,
                                "certainty": diag.certainty, "file": diag.file,
                                "line": diag.line, "column": diag.column,
                                "message": diag.message,
                                "fix_preview": diag.fix_preview})
    return diagnostics


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="openfoam-lint",
                                     description="Standalone OpenFOAM.com / ESI case linter")
    parser.add_argument("paths", nargs="+", help="files or case directories to lint")
    from hpc_gui.openfoam_core.release_support import supported_releases
    parser.add_argument("--release", choices=supported_releases(), default="v2312")
    parser.add_argument("--format", choices=("json", "text"), default="json")
    parser.add_argument("--fail-on", choices=("error", "warning"), default="error")
    args = parser.parse_args(argv)
    try:
        diags = _lint_paths(args.paths, release=args.release)
    except ValueError as exc:
        print(f"openfoam-lint: {exc}", file=sys.stderr)
        return 2
    errors = sum(1 for d in diags if d["severity"] == "error")
    warnings = sum(1 for d in diags if d["severity"] == "warning")
    if args.format == "json":
        print(json.dumps({"diagnostics": diags,
                          "counts": {"error": errors, "warning": warnings,
                                     "total": len(diags)},
                          "edition": "OpenFOAM.com / ESI",
                          "version": args.release,
                          "tool": "openfoam-linter",
                          "exit_policy": "0 clean, 1 error findings"}, indent=1))
    else:
        print(f"OpenFOAM.com / ESI {args.release}")
        for diag in diags:
            print(f"{diag['file']}:{diag['line']}:{diag['column']}: "
                  f"{diag['severity']} {diag['rule']}: {diag['message']}")
        print(f"{errors} error(s), {warnings} warning(s)")
    if args.fail_on == "warning":
        return 1 if (errors or warnings) else 0
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())

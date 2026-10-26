"""Standalone OpenFOAM Linter CLI (W65 LINT-013, G38).

Works with the Studio plugin uninstalled/disabled: imports only
``openfoam_lint`` engine modules. JSON stdout carries the same rule IDs,
severities and file/line/column anchors as the GUI path. Exit codes:
0 = no error-or-higher findings, 1 = errors found, 2 = usage/IO error.
"""

from __future__ import annotations

import argparse
import json
import os
import sys


def _lint_paths(paths: list[str]) -> list[dict]:
    from hpc_gui.plugins.openfoam_lint import api
    diags = []
    for path in paths:
        if os.path.isdir(path):
            targets = []
            for root, _, files in os.walk(path):
                targets += [os.path.join(root, f) for f in files
                            if f.endswith(("Dict", "Properties", "FoamFile"))]
        else:
            targets = [path]
        for target in targets:
            text = api.read_text_limited(target)
            for diag in api.lint_text(target, text):
                diags.append({"rule": diag.rule, "severity": diag.severity,
                              "certainty": diag.certainty, "file": diag.file,
                              "line": diag.line, "column": diag.column,
                              "message": diag.message, "fix_preview": diag.fix_preview})
    return diags


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="openfoam-lint",
                                     description="Standalone OpenFOAM case linter")
    parser.add_argument("paths", nargs="+", help="files or case directories to lint")
    parser.add_argument("--format", choices=("json", "text"), default="json")
    parser.add_argument("--fail-on", choices=("error", "warning"), default="error")
    args = parser.parse_args(argv)
    try:
        diags = _lint_paths(args.paths)
    except ValueError as exc:
        print(f"openfoam-lint: {exc}", file=sys.stderr)
        return 2
    errors = sum(1 for d in diags if d["severity"] == "error")
    warnings = sum(1 for d in diags if d["severity"] == "warning")
    if args.format == "json":
        print(json.dumps({"diagnostics": diags,
                          "counts": {"error": errors, "warning": warnings,
                                     "total": len(diags)},
                          "tool": "openfoam-linter",
                          "exit_policy": "0 clean, 1 error findings"}, indent=1))
    else:
        for diag in diags:
            print(f"{diag['file']}:{diag['line']}:{diag['column']}: "
                  f"{diag['severity']} {diag['rule']}: {diag['message']}")
        print(f"{errors} error(s), {warnings} warning(s)")
    if args.fail_on == "warning":
        return 1 if (errors or warnings) else 0
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())

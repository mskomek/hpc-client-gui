"""Report actual pytest taxonomy markers from collected test items."""
from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PRIMARY_CATEGORIES = (
    "unit", "integration", "gui", "e2e", "runtime_smoke",
    "contract", "audit", "reporting", "release",
)
QUALIFIERS = (
    "semantic", "regression", "performance", "resource", "concurrency",
    "slow", "subprocess", "windows", "linux", "macos", "hardware",
    "synthetic_hardware", "license", "acceptance", "artifact_dependent",
    "wx", "qt", "packaging",
)


def build_report(records: list[dict[str, Any]], repository_sha: str = "",
                 warnings: dict[str, Any] | None = None) -> dict[str, Any]:
    primary_counts = dict.fromkeys(PRIMARY_CATEGORIES, 0)
    qualifier_counts = dict.fromkeys(QUALIFIERS, 0)
    zero_primary, multi_primary = [], []
    for record in records:
        markers = set(record.get("markers", ()))
        primaries = [name for name in PRIMARY_CATEGORIES if name in markers]
        for name in primaries:
            primary_counts[name] += 1
        for name in QUALIFIERS:
            if name in markers:
                qualifier_counts[name] += 1
        if not primaries:
            zero_primary.append(record["nodeid"])
        elif len(primaries) > 1:
            multi_primary.append({"nodeid": record["nodeid"], "primaries": primaries})
    return {
        "schema_version": 1,
        "mode": "report",
        "repository_sha": repository_sha,
        "collection": {"total": len(records)},
        "primary_counts": primary_counts,
        "qualifier_counts": qualifier_counts,
        "zero_primary": {"count": len(zero_primary), "nodeids": zero_primary},
        "multi_primary": {"count": len(multi_primary), "nodes": multi_primary},
        "warnings": warnings or {"direct_test_calls": [], "catch_all_filenames": []},
    }


def find_direct_test_calls(sources: dict[str, str]) -> list[dict[str, Any]]:
    """Find clear direct calls to a locally defined or imported test_* function."""
    findings = []
    for path, source in sorted(sources.items()):
        try:
            tree = ast.parse(source, filename=path)
        except SyntaxError:
            continue
        imports = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for imported in node.names:
                    if imported.name.startswith("test_"):
                        imports[imported.asname or imported.name] = imported.name
        for function in ast.walk(tree):
            if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if not function.name.startswith("test_"):
                continue
            for call in ast.walk(function):
                if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Name):
                    continue
                local_name = call.func.id
                callee = imports.get(local_name)
                if callee is None and local_name.startswith("test_"):
                    callee = local_name
                if callee and callee != function.name:
                    findings.append({
                        "path": path, "caller": function.name,
                        "callee": callee, "line": call.lineno,
                    })
    return findings


def catch_all_filename_warnings(paths: list[str | Path]) -> list[str]:
    pattern = re.compile(r"missing_coverage|second_pass|final_gaps|misc_regressions", re.I)
    return sorted(str(path).replace("\\", "/")
                  for path in paths if pattern.search(Path(path).stem))


def _test_sources(test_root: Path) -> dict[str, str]:
    sources = {}
    for path in sorted(test_root.rglob("test_*.py")):
        try:
            sources[path.relative_to(ROOT).as_posix()] = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
    return sources


def collect_records() -> list[dict[str, Any]]:
    """Collect actual pytest items without running tests or printing all nodeids."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    import pytest

    class Collector:
        def __init__(self) -> None:
            self.records: list[dict[str, Any]] | None = None
            self.errors: list[str] = []

        def pytest_collection_finish(self, session: Any) -> None:
            self.records = [
                {"nodeid": item.nodeid,
                 "markers": [mark.name for mark in item.iter_markers()]}
                for item in session.items
            ]

        def pytest_collectreport(self, report: Any) -> None:
            if report.failed:
                self.errors.append(report.nodeid)

    collector = Collector()
    result = pytest.main(
        ["--collect-only", "-p", "no:terminal", "-p", "no:cacheprovider", str(ROOT / "tests")],
        plugins=[collector],
    )
    if result != pytest.ExitCode.OK or collector.records is None:
        details = ", ".join(collector.errors) or "no collection detail"
        raise RuntimeError(f"pytest collection failed (exit {int(result)}): {details}")
    return collector.records


def repository_sha() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
        capture_output=True, text=True,
    ).stdout.strip()


def write_json_report(report: dict[str, Any], output: str | Path) -> None:
    Path(output).write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def report_exit_code(report: dict[str, Any]) -> int:
    """Taxonomy debt and heuristic warnings do not fail REPORT mode."""
    return 0


def _print_report(report: dict[str, Any], json_out: str | None) -> None:
    print(f"Total collected: {report['collection']['total']}")
    for category, count in report["primary_counts"].items():
        print(f"{category}: {count}")
    print("Qualifier counts:")
    for qualifier, count in report["qualifier_counts"].items():
        print(f"  {qualifier}: {count}")
    print(f"Zero-primary: {report['zero_primary']['count']}")
    print(f"Multi-primary: {report['multi_primary']['count']}")
    if json_out:
        print(f"Complete nodeid lists: {json_out}")
    else:
        print("Zero-primary nodeids:")
        for nodeid in report["zero_primary"]["nodeids"]:
            print(nodeid)
    print("Multi-primary nodeids:")
    for node in report["multi_primary"]["nodes"]:
        print(f"{node['nodeid']} [{', '.join(node['primaries'])}]")
    for name, entries in report["warnings"].items():
        print(f"Warning {name}: {len(entries)}")
        for entry in entries:
            print(f"  {entry}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Report actual pytest taxonomy markers.")
    parser.add_argument("--mode", required=True, choices=("report",))
    parser.add_argument("--json-out", help="write the complete report to this path")
    args = parser.parse_args(argv)
    try:
        records = collect_records()
        test_root = ROOT / "tests"
        sources = _test_sources(test_root)
        test_files = [
            path.relative_to(ROOT).as_posix() for path in test_root.rglob("test_*.py")
        ]
        warnings = {
            "direct_test_calls": find_direct_test_calls(sources),
            "catch_all_filenames": catch_all_filename_warnings(test_files),
        }
        report = build_report(records, repository_sha(), warnings)
        if args.json_out:
            write_json_report(report, args.json_out)
        _print_report(report, args.json_out)
        return report_exit_code(report)
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"taxonomy report failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

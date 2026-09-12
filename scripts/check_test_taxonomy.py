"""Report actual pytest taxonomy markers from collected test items."""
from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SEMANTIC_REVIEW_PATH = (
    ROOT / "audit" / "archive" / "87e1e709" / "test-suite-baseline"
    / "semantic-taxonomy-review.json"
)
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
    primary_by_nodeid = {}
    for record in records:
        markers = set(record.get("markers", ()))
        primaries = [name for name in PRIMARY_CATEGORIES if name in markers]
        if primaries:
            primary_by_nodeid[record["nodeid"]] = primaries
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
        "nodeids": [record["nodeid"] for record in records],
        "primary_counts": primary_counts,
        "qualifier_counts": qualifier_counts,
        "primary_by_nodeid": primary_by_nodeid,
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


def build_ratchet_report(report: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    baseline_nodes = set(baseline["nodeids"])
    baseline_zero = set(baseline["zero_primary_nodeids"])
    current_nodes = set(report["nodeids"])
    current_zero = set(report["zero_primary"]["nodeids"])
    current_primary = report["primary_by_nodeid"]
    current_multi = report["multi_primary"]["nodes"]
    new_nodes = current_nodes - baseline_nodes
    removed_nodes = baseline_nodes - current_nodes
    new_catch_all = sorted(
        set(report["warnings"]["catch_all_filenames"])
        - set(baseline["catch_all_filenames"])
    )
    lost_classification = sorted(
        nodeid for nodeid in baseline["primary_by_nodeid"]
        if nodeid in current_nodes and nodeid not in current_primary
    )
    new_invalid_classification = sorted(
        nodeid for nodeid in new_nodes
        if len(current_primary.get(nodeid, ())) != 1
    )
    new_zero = sorted(current_zero - baseline_zero)
    passed = (
        not new_zero
        and len(current_zero) <= baseline["zero_primary_count"]
        and len(current_multi) <= baseline["multi_primary_count"]
        and not lost_classification
        and not new_invalid_classification
        and not new_catch_all
    )
    return {
        "schema_version": 1,
        "mode": "ratchet",
        "repository_sha": report["repository_sha"],
        "baseline_sha": baseline["repository_sha"],
        "passed": passed,
        "baseline": {
            "node_count": len(baseline_nodes),
            "zero_primary_count": baseline["zero_primary_count"],
            "multi_primary_count": baseline["multi_primary_count"],
        },
        "current": {
            "node_count": len(current_nodes),
            "zero_primary_count": len(current_zero),
            "multi_primary_count": len(current_multi),
        },
        "added_nodeids": sorted(new_nodes),
        "removed_nodeids": sorted(removed_nodes),
        "new_zero_primary_nodeids": new_zero,
        "lost_classification_nodeids": lost_classification,
        "new_nodes_without_exactly_one_primary": new_invalid_classification,
        "new_catch_all_files": new_catch_all,
    }


def load_ratchet_baseline(path: str | Path) -> dict[str, Any]:
    baseline = json.loads(Path(path).read_text(encoding="utf-8"))
    nodeids = baseline.get("nodeids")
    zero = baseline.get("zero_primary_nodeids")
    primary = baseline.get("primary_by_nodeid")
    catch_all = baseline.get("catch_all_filenames")
    if (
        baseline.get("schema_version") != 1
        or not isinstance(baseline.get("repository_sha"), str)
        or not isinstance(nodeids, list)
        or not all(isinstance(nodeid, str) for nodeid in nodeids)
        or len(set(nodeids)) != len(nodeids)
        or not isinstance(zero, list)
        or not all(isinstance(nodeid, str) for nodeid in zero)
        or len(set(zero)) != len(zero)
        or not set(zero).issubset(nodeids)
        or baseline.get("zero_primary_count") != len(zero)
        or baseline.get("collection_count") != len(nodeids)
        or not isinstance(primary, dict)
        or any(nodeid not in nodeids for nodeid in primary)
        or set(zero).intersection(primary)
        or any(
            not isinstance(markers, list)
            or not markers
            or not all(isinstance(marker, str) and marker in PRIMARY_CATEGORIES for marker in markers)
            for markers in primary.values()
        )
        or not isinstance(catch_all, list)
        or type(baseline.get("multi_primary_count")) is not int
        or baseline["multi_primary_count"] < 0
    ):
        raise ValueError("invalid taxonomy ratchet baseline")
    return baseline


def ratchet_exit_code(result: dict[str, Any]) -> int:
    return 0 if result["passed"] else 1


def registered_markers() -> set[str]:
    """Read pytest's declared custom markers from the repository config."""
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    entries = config["tool"]["pytest"]["ini_options"]["markers"]
    return {entry.partition(":")[0].strip() for entry in entries}


def build_enforce_report(
    report: dict[str, Any], registered: set[str],
    semantic_review: dict[str, Any] | None = None,
) -> dict[str, Any]:
    known = set(PRIMARY_CATEGORIES) | set(QUALIFIERS)
    unknown_registered = sorted(registered - known)
    missing_registered = sorted(known - registered)
    if semantic_review is None:
        semantic_review = {
            "passed": False,
            "reviewed_count": 0,
            "missing_nodeids": report["nodeids"],
            "unknown_nodeids": [],
            "unreviewed_nodeids": [],
            "invalid_nodeids": [],
            "marker_mismatch_nodeids": [],
            "errors": ["semantic review document was not loaded"],
        }
    passed = not (
        report["zero_primary"]["count"]
        or report["multi_primary"]["count"]
        or unknown_registered
        or missing_registered
        or not semantic_review["passed"]
    )
    return {
        "schema_version": 1,
        "mode": "enforce",
        "repository_sha": report["repository_sha"],
        "passed": passed,
        "zero_primary": report["zero_primary"],
        "multi_primary": report["multi_primary"],
        "unknown_registered_markers": unknown_registered,
        "missing_registered_markers": missing_registered,
        "semantic_review": semantic_review,
        "warnings": report["warnings"],
    }


def build_semantic_review_report(
    records: list[dict[str, Any]], document: dict[str, Any] | None,
) -> dict[str, Any]:
    """Require an evidence-backed review matching every collected marker set."""
    errors = []
    entries = document.get("nodes") if isinstance(document, dict) else None
    if not isinstance(entries, list):
        entries = []
        errors.append("review document must contain a nodes array")
    if not isinstance(document, dict) or document.get("schema_version") != 1:
        errors.append("review document schema_version must be 1")

    by_nodeid: dict[str, dict[str, Any]] = {}
    duplicate_entries = set()
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("nodeid"), str):
            errors.append("each review entry must have a string nodeid")
            continue
        nodeid = entry["nodeid"]
        if nodeid in by_nodeid:
            duplicate_entries.add(nodeid)
        by_nodeid[nodeid] = entry

    current = {record["nodeid"]: record for record in records}
    missing = sorted(set(current) - set(by_nodeid))
    unknown = sorted(set(by_nodeid) - set(current))
    unreviewed = []
    invalid = set(duplicate_entries)
    marker_mismatch = set()
    for nodeid, entry in by_nodeid.items():
        if nodeid not in current:
            continue
        if entry.get("reviewed") is not True:
            unreviewed.append(nodeid)
        if not isinstance(entry.get("evidence"), str) or not entry["evidence"].strip():
            invalid.add(nodeid)
        primary = entry.get("primary")
        qualifiers = entry.get("qualifiers")
        if (
            primary not in PRIMARY_CATEGORIES
            or not isinstance(qualifiers, list)
            or not all(isinstance(value, str) and value in QUALIFIERS for value in qualifiers)
            or len(set(qualifiers)) != len(qualifiers)
        ):
            invalid.add(nodeid)
            continue
        markers = set(current[nodeid].get("markers", ()))
        actual_primary = [value for value in PRIMARY_CATEGORIES if value in markers]
        actual_qualifiers = sorted(value for value in QUALIFIERS if value in markers)
        if actual_primary != [primary] or sorted(qualifiers) != actual_qualifiers:
            marker_mismatch.add(nodeid)
        behavior_id = entry.get("behavior_id")
        if behavior_id is not None and (
            not isinstance(behavior_id, str) or not behavior_id.strip()
        ):
            invalid.add(nodeid)

    reviewed_count = sum(
        1 for nodeid, entry in by_nodeid.items()
        if nodeid in current and entry.get("reviewed") is True
    )
    passed = not (
        errors or missing or unknown or unreviewed or invalid or marker_mismatch
    )
    return {
        "passed": passed,
        "reviewed_count": reviewed_count,
        "expected_count": len(current),
        "missing_nodeids": missing,
        "unknown_nodeids": unknown,
        "unreviewed_nodeids": sorted(unreviewed),
        "invalid_nodeids": sorted(invalid),
        "marker_mismatch_nodeids": sorted(marker_mismatch),
        "errors": errors,
    }


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


def _print_ratchet(result: dict[str, Any], json_out: str | None) -> None:
    print(f"Ratchet: {'PASS' if result['passed'] else 'FAIL'}")
    print(f"Zero-primary: {result['baseline']['zero_primary_count']} baseline, "
          f"{result['current']['zero_primary_count']} current")
    print(f"Multi-primary: {result['baseline']['multi_primary_count']} baseline, "
          f"{result['current']['multi_primary_count']} current")
    for key in (
        "added_nodeids", "removed_nodeids", "new_zero_primary_nodeids",
        "lost_classification_nodeids", "new_nodes_without_exactly_one_primary",
        "new_catch_all_files",
    ):
        print(f"{key}: {result[key]}")
    if json_out:
        print(f"Complete result: {json_out}")


def _print_enforce(result: dict[str, Any], json_out: str | None) -> None:
    print(f"Taxonomy enforce: {'PASS' if result['passed'] else 'FAIL'}")
    print(f"Zero-primary: {result['zero_primary']['count']}")
    print(f"Multi-primary: {result['multi_primary']['count']}")
    print(f"Unknown registered markers: {result['unknown_registered_markers']}")
    print(f"Missing registered markers: {result['missing_registered_markers']}")
    review = result["semantic_review"]
    print(f"Semantic review: {'PASS' if review['passed'] else 'FAIL'}")
    print(f"Semantic review complete: {review['reviewed_count']}/{review['expected_count']}")
    print(f"Semantic review gaps: missing={len(review['missing_nodeids'])}, "
          f"unreviewed={len(review['unreviewed_nodeids'])}, "
          f"invalid={len(review['invalid_nodeids'])}, "
          f"marker mismatch={len(review['marker_mismatch_nodeids'])}, "
          f"unknown={len(review['unknown_nodeids'])}")
    for name, entries in result["warnings"].items():
        print(f"Warning {name}: {len(entries)}")
    if json_out:
        print(f"Complete result: {json_out}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Report, ratchet, or enforce actual pytest taxonomy markers.")
    parser.add_argument("--mode", required=True, choices=("report", "ratchet", "enforce"))
    parser.add_argument("--json-out", help="write the complete report to this path")
    parser.add_argument("--baseline", help="exact taxonomy baseline required for ratchet mode")
    parser.add_argument(
        "--semantic-review", default=str(SEMANTIC_REVIEW_PATH),
        help="per-node semantic review JSON required by enforce mode",
    )
    args = parser.parse_args(argv)
    if args.mode == "ratchet" and not args.baseline:
        parser.error("--baseline is required for ratchet mode")
    if args.mode == "report" and args.baseline:
        parser.error("--baseline is only valid for ratchet mode")
    if args.mode == "enforce" and args.baseline:
        parser.error("--baseline is only valid for ratchet mode")
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
        if args.mode == "report":
            result = report
            _print_report(report, args.json_out)
            exit_code = report_exit_code(report)
        elif args.mode == "ratchet":
            result = build_ratchet_report(report, load_ratchet_baseline(args.baseline))
            _print_ratchet(result, args.json_out)
            exit_code = ratchet_exit_code(result)
        else:
            try:
                document = json.loads(Path(args.semantic_review).read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                document = None
            semantic_review = build_semantic_review_report(records, document)
            result = build_enforce_report(report, registered_markers(), semantic_review)
            _print_enforce(result, args.json_out)
            exit_code = 0 if result["passed"] else 1
        if args.json_out:
            write_json_report(result, args.json_out)
        return exit_code
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
        print(f"taxonomy report failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

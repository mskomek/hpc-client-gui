"""Enforce the first-party 500-line source limit against a repository allowlist.

Scans ``src``, ``tests``, ``scripts``, ``devtools`` and ``tools`` for ``.py`` files
and counts physical lines. A file above ``LIMIT`` must have an unexpired entry in
``scripts/line_limit_allowlist.json`` whose recorded ``loc`` is not below the
current count. The check also fails on stale entries (file now within the limit
or missing) and on entries whose schema is incomplete. Files from
``WARNING_FROM`` through ``LIMIT`` are reported as warnings only.

Exclusions are explicit: see ``EXCLUDED_DIR_NAMES``, ``EXCLUDED_DIR_SUFFIXES``
and ``EXCLUDED_FILE_NAMES``. They are covered by tests.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ALLOWLIST = ROOT / "scripts" / "line_limit_allowlist.json"
SCAN_ROOTS = ("src", "tests", "scripts", "devtools", "tools")
LIMIT = 500
WARNING_FROM = 400

# Vendor, generated and cache directories that are not first-party source.
EXCLUDED_DIR_NAMES = frozenset(
    {"__pycache__", ".venv", "venv", "build", "dist", "node_modules", "vendor", "third_party"}
)
EXCLUDED_DIR_SUFFIXES = (".egg-info",)
# Generated files that live inside scanned roots; none are currently required.
EXCLUDED_FILE_NAMES: frozenset[str] = frozenset()

REQUIRED_KEYS = ("path", "loc", "reason", "expiry", "migration_target")


def physical_lines(path: Path) -> int:
    return len(path.read_bytes().decode("utf-8", "replace").splitlines())


def is_excluded(relative: Path) -> bool:
    if relative.name in EXCLUDED_FILE_NAMES:
        return True
    for part in relative.parts[:-1]:
        if part in EXCLUDED_DIR_NAMES or part.endswith(EXCLUDED_DIR_SUFFIXES):
            return True
    return False


def first_party_counts(root: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    for scan_root in SCAN_ROOTS:
        base = root / scan_root
        if not base.is_dir():
            continue
        for path in base.rglob("*.py"):
            relative = path.relative_to(root)
            if not is_excluded(relative):
                counts[relative.as_posix()] = physical_lines(path)
    return counts


def load_allowlist(path: Path) -> tuple[int, list[dict[str, Any]], list[str]]:
    """Return (declared limit, entries, schema errors)."""
    errors: list[str] = []
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("limit") != LIMIT:
        errors.append(f"allowlist limit {data.get('limit')!r} must equal {LIMIT}")
    entries = data.get("entries", [])
    for index, entry in enumerate(entries):
        missing = [key for key in REQUIRED_KEYS if not entry.get(key)]
        if missing:
            errors.append(f"entry {index} missing {missing}")
            continue
        if not isinstance(entry["loc"], int):
            errors.append(f"{entry['path']}: loc must be an integer")
        try:
            dt.date.fromisoformat(str(entry["expiry"]))
        except ValueError:
            errors.append(f"{entry['path']}: expiry {entry['expiry']!r} is not an ISO date")
    return LIMIT, entries, errors


def evaluate(counts: dict[str, int], entries: list[dict[str, Any]], today: dt.date) -> dict[str, list[str]]:
    violations: list[str] = []
    warnings: list[str] = []
    by_path: dict[str, dict[str, Any]] = {}
    for entry in entries:
        if entry.get("path") in by_path:
            violations.append(f"{entry['path']}: duplicate allowlist entry")
        by_path[entry.get("path")] = entry
    for rel, loc in sorted(counts.items()):
        entry = by_path.pop(rel, None)
        if loc <= LIMIT:
            if entry is not None:
                violations.append(f"{rel}: {loc} lines is within the limit; remove its allowlist entry")
            elif loc >= WARNING_FROM:
                warnings.append(f"{rel}: {loc} lines is in the 400-500 warning zone")
            continue
        if entry is None:
            violations.append(f"{rel}: {loc} lines exceeds {LIMIT} and is not in the allowlist")
            continue
        if loc > entry["loc"]:
            violations.append(f"{rel}: {loc} lines grew beyond recorded {entry['loc']}")
        elif loc < entry["loc"]:
            warnings.append(f"{rel}: recorded {entry['loc']} lines is above current {loc}; lower it")
        if today > dt.date.fromisoformat(str(entry["expiry"])):
            violations.append(f"{rel}: allowlist entry expired on {entry['expiry']}")
    for rel in sorted(by_path):
        violations.append(f"{rel}: allowlist entry has no matching first-party file")
    return {"violations": violations, "warnings": warnings}


def run_check(root: Path = ROOT, allowlist: Path = ALLOWLIST, today: dt.date | None = None) -> dict[str, Any]:
    today = today or dt.date.today()
    counts = first_party_counts(root)
    _, entries, schema_errors = load_allowlist(allowlist)
    result = evaluate(counts, entries, today)
    result["violations"] = schema_errors + result["violations"]
    result["schema_errors"] = schema_errors
    result["over_limit"] = {rel: loc for rel, loc in sorted(counts.items()) if loc > LIMIT}
    result["file_count"] = len(counts)
    result["ok"] = not result["violations"]
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--allowlist", type=Path, default=ALLOWLIST)
    parser.add_argument("--today", type=dt.date.fromisoformat, default=None)
    parser.add_argument("--report", type=Path, default=None, help="write the JSON result here")
    args = parser.parse_args(argv)
    result = run_check(args.root, args.allowlist, args.today)
    if args.report:
        args.report.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"first-party files scanned: {result['file_count']}")
    print(f"over {LIMIT} lines: {len(result['over_limit'])}")
    for line in result["warnings"]:
        print(f"WARNING {line}")
    for line in result["violations"]:
        print(f"VIOLATION {line}")
    print("line-limit check:", "PASS" if result["ok"] else "FAIL")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())

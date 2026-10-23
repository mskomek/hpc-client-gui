"""Architecture contract: first-party files stay within the 500-line limit or an allowlist entry."""

from __future__ import annotations

import datetime as dt
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location("check_line_limits", ROOT / "scripts" / "check_line_limits.py")
clc = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(clc)

TODAY = dt.date(2026, 10, 22)
EXPIRY = "2026-12-31"


def _entry(path: str, loc: int, expiry: str = EXPIRY) -> dict:
    return {
        "path": path,
        "loc": loc,
        "reason": "test entry",
        "expiry": expiry,
        "migration_target": "split test",
    }


def _write_tree(root: Path, files: dict[str, int]) -> None:
    for rel, lines in files.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("x = 1\n" * lines, encoding="utf-8")


def _write_allowlist(path: Path, entries: list[dict]) -> Path:
    path.write_text(json.dumps({"limit": 500, "entries": entries}), encoding="utf-8")
    return path


@pytest.mark.audit
def test_repo_first_party_files_respect_limit_or_allowlist():
    result = clc.run_check(ROOT, ROOT / "scripts" / "line_limit_allowlist.json", TODAY)
    assert result["violations"] == [], result["violations"]
    assert result["file_count"] > 0


@pytest.mark.audit
def test_repo_allowlist_entries_are_complete_and_time_boxed():
    _, entries, schema_errors = clc.load_allowlist(ROOT / "scripts" / "line_limit_allowlist.json")
    assert schema_errors == []
    assert entries, "allowlist must list every current over-limit file"
    for entry in entries:
        assert entry["reason"].strip()
        assert entry["migration_target"].strip()
        assert dt.date.fromisoformat(entry["expiry"]) >= TODAY


@pytest.mark.audit
@pytest.mark.parametrize("lines,expected_ok", [(500, True), (501, False)])
def test_limit_boundary_is_inclusive_at_500(tmp_path, lines, expected_ok):
    _write_tree(tmp_path, {"src/mod.py": lines})
    result = clc.run_check(tmp_path, _write_allowlist(tmp_path / "al.json", []), TODAY)
    assert result["ok"] is expected_ok


@pytest.mark.audit
def test_unlisted_oversized_file_fails(tmp_path):
    _write_tree(tmp_path, {"tests/big.py": 900})
    result = clc.run_check(tmp_path, _write_allowlist(tmp_path / "al.json", []), TODAY)
    assert any("not in the allowlist" in v for v in result["violations"])


@pytest.mark.audit
def test_listed_oversized_file_passes_within_recorded_loc(tmp_path):
    _write_tree(tmp_path, {"src/big.py": 700})
    allow = _write_allowlist(tmp_path / "al.json", [_entry("src/big.py", 700)])
    assert clc.run_check(tmp_path, allow, TODAY)["ok"] is True


@pytest.mark.audit
def test_grown_file_beyond_recorded_loc_fails(tmp_path):
    _write_tree(tmp_path, {"src/big.py": 701})
    allow = _write_allowlist(tmp_path / "al.json", [_entry("src/big.py", 700)])
    result = clc.run_check(tmp_path, allow, TODAY)
    assert any("grew beyond recorded 700" in v for v in result["violations"])


@pytest.mark.audit
def test_stale_entry_for_file_now_within_limit_fails(tmp_path):
    _write_tree(tmp_path, {"src/small.py": 300})
    allow = _write_allowlist(tmp_path / "al.json", [_entry("src/small.py", 700)])
    result = clc.run_check(tmp_path, allow, TODAY)
    assert any("within the limit" in v for v in result["violations"])


@pytest.mark.audit
def test_entry_for_missing_file_fails(tmp_path):
    _write_tree(tmp_path, {"src/other.py": 10})
    allow = _write_allowlist(tmp_path / "al.json", [_entry("src/gone.py", 700)])
    result = clc.run_check(tmp_path, allow, TODAY)
    assert any("no matching first-party file" in v for v in result["violations"])


@pytest.mark.audit
def test_expired_entry_fails(tmp_path):
    _write_tree(tmp_path, {"src/big.py": 700})
    allow = _write_allowlist(tmp_path / "al.json", [_entry("src/big.py", 700, expiry="2026-10-21")])
    result = clc.run_check(tmp_path, allow, TODAY)
    assert any("expired" in v for v in result["violations"])


@pytest.mark.audit
def test_warning_zone_is_reported_without_failing(tmp_path):
    _write_tree(tmp_path, {"src/warm.py": 450})
    result = clc.run_check(tmp_path, _write_allowlist(tmp_path / "al.json", []), TODAY)
    assert result["ok"] is True
    assert any("warning zone" in w for w in result["warnings"])


@pytest.mark.audit
def test_schema_errors_fail_closed(tmp_path):
    _write_tree(tmp_path, {"src/a.py": 1})
    bad = {"path": "src/a.py", "loc": 1, "reason": "", "expiry": "not-a-date", "migration_target": "x"}
    result = clc.run_check(tmp_path, _write_allowlist(tmp_path / "al.json", [bad]), TODAY)
    assert result["ok"] is False
    assert any("missing" in e or "ISO date" in e for e in result["schema_errors"])


@pytest.mark.audit
def test_exclusions_are_explicit_and_skipped(tmp_path):
    assert clc.EXCLUDED_DIR_NAMES == frozenset(
        {"__pycache__", ".venv", "venv", "build", "dist", "node_modules", "vendor", "third_party"}
    )
    assert clc.EXCLUDED_DIR_SUFFIXES == (".egg-info",)
    assert clc.EXCLUDED_FILE_NAMES == frozenset()
    _write_tree(
        tmp_path,
        {
            "src/pkg/__pycache__/cached.py": 900,
            "src/pkg.egg-info/gen.py": 900,
            "src/vendor/lib.py": 900,
            "tests/build/x.py": 900,
            "src/real.py": 10,
        },
    )
    counts = clc.first_party_counts(tmp_path)
    assert counts == {"src/real.py": 10}


@pytest.mark.audit
def test_scan_roots_are_explicit():
    assert clc.SCAN_ROOTS == ("src", "tests", "scripts", "devtools", "tools")

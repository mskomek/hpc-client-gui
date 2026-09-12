from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import check_test_taxonomy as checker  # noqa: E402


@pytest.mark.audit
def test_unmarked_record_is_zero_primary():
    report = checker.build_report([{"nodeid": "tests/a.py::test_a", "markers": []}])
    assert report["zero_primary"] == {
        "count": 1,
        "nodeids": ["tests/a.py::test_a"],
    }


@pytest.mark.audit
def test_single_primary_is_counted_once():
    report = checker.build_report(
        [{"nodeid": "tests/a.py::test_a", "markers": ["unit"]}]
    )
    assert report["primary_counts"]["unit"] == 1
    assert report["zero_primary"]["count"] == 0


@pytest.mark.audit
def test_two_primary_markers_are_reported():
    report = checker.build_report(
        [{"nodeid": "tests/a.py::test_a", "markers": ["gui", "integration"]}]
    )
    assert report["multi_primary"] == {
        "count": 1,
        "nodes": [
            {
                "nodeid": "tests/a.py::test_a",
                "primaries": ["integration", "gui"],
            }
        ],
    }


@pytest.mark.audit
def test_qualifiers_do_not_count_as_primaries():
    report = checker.build_report(
        [{"nodeid": "tests/a.py::test_a", "markers": ["slow", "wx", "packaging"]}]
    )
    assert report["zero_primary"]["count"] == 1
    assert report["qualifier_counts"]["slow"] == 1
    assert report["qualifier_counts"]["wx"] == 1
    assert report["qualifier_counts"]["packaging"] == 1


@pytest.mark.audit
def test_json_keeps_exact_nodeids(tmp_path):
    nodeids = [
        "tests/test_a.py::TestCase::test_a[param one]",
        "tests/test_b.py::test_b",
    ]
    report = checker.build_report(
        [{"nodeid": nodeid, "markers": []} for nodeid in nodeids]
    )
    output = tmp_path / "report.json"
    checker.write_json_report(report, output)
    assert json.loads(output.read_text(encoding="utf-8"))["zero_primary"]["nodeids"] == nodeids


@pytest.mark.audit
def test_report_mode_succeeds_with_taxonomy_debt(monkeypatch, capsys):
    monkeypatch.setattr(
        checker,
        "collect_records",
        lambda: [{"nodeid": "tests/legacy.py::test_unmarked", "markers": []}],
    )
    assert checker.main(["--mode", "report"]) == 0
    assert "Zero-primary: 1" in capsys.readouterr().out


@pytest.mark.audit
def test_collection_failure_returns_nonzero(monkeypatch, capsys):
    def fail_collection():
        raise RuntimeError("synthetic collection failure")

    monkeypatch.setattr(checker, "collect_records", fail_collection)
    assert checker.main(["--mode", "report"]) != 0
    assert "synthetic collection failure" in capsys.readouterr().err


@pytest.mark.audit
def test_direct_test_call_warning_finds_imported_test_function():
    findings = checker.find_direct_test_calls(
        {
            "tests/test_a.py": (
                "from tests.test_b import test_inner as run_inner\n"
                "def test_outer():\n"
                "    run_inner()\n"
            )
        }
    )
    assert findings == [
        {
            "path": "tests/test_a.py",
            "caller": "test_outer",
            "callee": "test_inner",
            "line": 3,
        }
    ]


@pytest.mark.audit
def test_catch_all_filename_is_warning_only():
    warnings = checker.catch_all_filename_warnings(
        ["tests/test_final_gaps.py", "tests/test_wave80_files_outputs.py"]
    )
    report = checker.build_report(
        [{"nodeid": "tests/test_final_gaps.py::test_a", "markers": []}],
        warnings={"catch_all_filenames": warnings},
    )
    assert warnings == ["tests/test_final_gaps.py"]
    assert checker.report_exit_code(report) == 0

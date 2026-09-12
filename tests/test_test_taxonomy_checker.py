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


def _ratchet_baseline(report):
    return {
        "schema_version": 1,
        "repository_sha": "baseline-sha",
        "collection_count": report["collection"]["total"],
        "nodeids": report["nodeids"],
        "zero_primary_count": report["zero_primary"]["count"],
        "zero_primary_nodeids": report["zero_primary"]["nodeids"],
        "multi_primary_count": report["multi_primary"]["count"],
        "primary_by_nodeid": report["primary_by_nodeid"],
        "catch_all_filenames": report["warnings"]["catch_all_filenames"],
    }


@pytest.mark.audit
def test_ratchet_allows_existing_debt_and_requires_new_tests_classified():
    baseline_report = checker.build_report(
        [
            {"nodeid": "tests/legacy.py::test_old", "markers": []},
            {"nodeid": "tests/core.py::test_known", "markers": ["unit"]},
        ]
    )
    current_report = checker.build_report(
        [
            {"nodeid": "tests/legacy.py::test_old", "markers": []},
            {"nodeid": "tests/core.py::test_known", "markers": ["unit"]},
            {"nodeid": "tests/new.py::test_new", "markers": ["audit"]},
        ],
        repository_sha="current-sha",
    )

    result = checker.build_ratchet_report(current_report, _ratchet_baseline(baseline_report))

    assert result["passed"] is True
    assert result["added_nodeids"] == ["tests/new.py::test_new"]
    assert result["new_zero_primary_nodeids"] == []


@pytest.mark.audit
def test_ratchet_rejects_new_zero_multi_and_lost_classification():
    baseline_report = checker.build_report(
        [
            {"nodeid": "tests/legacy.py::test_old", "markers": []},
            {"nodeid": "tests/core.py::test_known", "markers": ["unit"]},
        ]
    )
    current_report = checker.build_report(
        [
            {"nodeid": "tests/legacy.py::test_old", "markers": []},
            {"nodeid": "tests/core.py::test_known", "markers": []},
            {"nodeid": "tests/new.py::test_unmarked", "markers": []},
            {"nodeid": "tests/new.py::test_multi", "markers": ["gui", "unit"]},
        ]
    )

    result = checker.build_ratchet_report(current_report, _ratchet_baseline(baseline_report))

    assert result["passed"] is False
    assert result["new_zero_primary_nodeids"] == [
        "tests/core.py::test_known",
        "tests/new.py::test_unmarked",
    ]
    assert result["lost_classification_nodeids"] == ["tests/core.py::test_known"]
    assert result["new_nodes_without_exactly_one_primary"] == [
        "tests/new.py::test_multi",
        "tests/new.py::test_unmarked",
    ]


@pytest.mark.audit
def test_ratchet_rejects_new_generic_catch_all_file():
    baseline_report = checker.build_report([], warnings={"catch_all_filenames": []})
    current_report = checker.build_report(
        [{"nodeid": "tests/test_new.py::test_new", "markers": ["audit"]}],
        warnings={"catch_all_filenames": ["tests/test_final_gaps.py"]},
    )

    result = checker.build_ratchet_report(current_report, _ratchet_baseline(baseline_report))

    assert result["passed"] is False
    assert result["new_catch_all_files"] == ["tests/test_final_gaps.py"]


@pytest.mark.audit
def test_ratchet_reports_removed_node_without_blocking_intentional_cleanup():
    baseline_report = checker.build_report(
        [{"nodeid": "tests/legacy.py::test_removed", "markers": []}]
    )
    current_report = checker.build_report([])

    result = checker.build_ratchet_report(current_report, _ratchet_baseline(baseline_report))

    assert result["passed"] is True
    assert result["removed_nodeids"] == ["tests/legacy.py::test_removed"]

import pytest

from hpc_gui.services.parity_matrix import Evidence, render_status


def test_parity_report_generation_contains_all_baseline_ids():
    baseline = "| GUI-TEST-001 | P0 |\n| GUI-TEST-002 | P1 |"
    mapping = {item: Evidence("COVERED", "qt", "wx", "test") for item in ("GUI-TEST-001", "GUI-TEST-002")}
    report = render_status(baseline, mapping)
    assert "# V2 Parity Status" in report and report.count("GUI-TEST-") == 2


def test_parity_report_rejects_missing_mapping():
    with pytest.raises(ValueError, match="missing parity mapping"):
        render_status("GUI-TEST-001", {})


def test_parity_report_requires_intentional_change_justification():
    mapping = {"GUI-TEST-001": Evidence("INTENTIONALLY_CHANGED", "qt", "wx", "test")}
    with pytest.raises(ValueError, match="justification"):
        render_status("GUI-TEST-001", mapping)

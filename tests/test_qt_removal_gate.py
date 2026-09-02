from hpc_gui.services.parity_matrix import Evidence, render_status
from scripts.qt_removal_gate import evaluate_gate


def test_qt_removal_gate_reports_no_go_for_partial_p0_and_qt_dependency():
    baseline = "| GUI-SHELL-001 | thing | P0 |\n| GUI-SHELL-002 | thing | P1 |"
    status = render_status(baseline, {"GUI-SHELL-001": Evidence("PARTIAL", "qt", "wx", "test"), "GUI-SHELL-002": Evidence("COVERED", "qt", "wx", "test")})
    report = evaluate_gate(baseline, status, 'dependencies = ["PySide6>=6.5"]')
    assert report["decision"] == "NO-GO"
    assert any("P0 not covered" in reason for reason in report["reasons"])
    assert report["qt_dependencies"]

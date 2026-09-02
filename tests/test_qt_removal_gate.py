from hpc_gui.services.parity_matrix import Evidence, render_status
from scripts.qt_removal_gate import evaluate_gate, production_qt_imports


def test_qt_removal_gate_reports_no_go_for_partial_p0_and_qt_dependency():
    baseline = "| GUI-SHELL-001 | thing | P0 |\n| GUI-SHELL-002 | thing | P1 |"
    status = render_status(baseline, {"GUI-SHELL-001": Evidence("PARTIAL", "qt", "wx", "test"), "GUI-SHELL-002": Evidence("COVERED", "qt", "wx", "test")})
    report = evaluate_gate(baseline, status, 'dependencies = ["PySide6>=6.5"]', ["src/hpc_gui/app.py"], qt_imports=[{"path": "src/hpc_gui/app.py", "line": 1, "import": "PySide6"}])
    assert report["decision"] == "NO-GO"
    assert any("P0 not covered" in reason for reason in report["reasons"])
    assert report["qt_dependencies"]
    assert report["qt_files"] == ["src/hpc_gui/app.py"]
    assert report["qt_imports"][0]["line"] == 1


def test_ast_scanner_ignores_comments_and_docstrings(tmp_path):
    source = tmp_path / "src" / "hpc_gui"
    source.mkdir(parents=True)
    (source / "safe.py").write_text('"""PySide6 mention only."""\n# from PySide6 import QtCore\n', encoding="utf-8")
    assert production_qt_imports(tmp_path) == []


def test_dependency_only_qt_is_still_no_go():
    report = evaluate_gate("", "", 'dependencies = ["PySide6>=6.5"]', packaged_evidence=True, manual_evidence=True)
    assert report["decision"] == "NO-GO" and not report["qt_imports"]


def test_true_go_fixture_requires_all_removal_evidence():
    baseline = "| GUI-SHELL-001 | thing | P0 |"
    status = render_status(baseline, {"GUI-SHELL-001": Evidence("COVERED", "qt", "wx", "test")})
    report = evaluate_gate(baseline, status, "", packaged_evidence=True, manual_evidence=True)
    assert report["decision"] == "GO"

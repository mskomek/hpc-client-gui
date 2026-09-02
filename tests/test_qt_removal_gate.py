from scripts.qt_removal_gate import MANUAL_CHECKS, PACKAGED_CHECKS, dependency_records, evaluate_gate, packaging_blockers, production_qt_imports

SHA = "a" * 40


def gate(**overrides):
    values = {"p0": {"GUI-TEST-001": "COVERED"}, "qt_imports": [], "qt_dependencies": [], "qt_packaging": [], "default_runtime": "wx", "packaged": {p: "PASS" for p in ("windows", "linux", "macos")}, "manual": {p: "PASS" for p in ("windows", "linux", "macos")}, "commit": SHA}
    values.update(overrides)
    return evaluate_gate(**values)


def test_ast_imports_block_but_comments_and_docstrings_do_not(tmp_path):
    source = tmp_path / "src" / "hpc_gui"
    source.mkdir(parents=True)
    (source / "safe.py").write_text('"""PySide6 mention."""\n# import PySide6\n', encoding="utf-8")
    assert production_qt_imports(tmp_path) == []
    (source / "bad.py").write_text("import PySide6.QtWidgets\nfrom PySide6.QtCore import QObject\n", encoding="utf-8")
    assert [item["import"] for item in production_qt_imports(tmp_path)] == ["PySide6.QtWidgets", "PySide6.QtCore"]


def test_dependency_names_are_normalized(tmp_path):
    (tmp_path / "requirements.txt").write_text("pyside-6>=6\nshiboken6\n", encoding="utf-8")
    records = dependency_records(tmp_path)
    assert {item["dependency"] for item in records} == {"pyside-6", "shiboken6"}
    assert gate(qt_dependencies=records)[0] == "NO-GO"


def test_packaging_scanner_ignores_excludes_and_comments(tmp_path):
    build = tmp_path / "build"
    build.mkdir()
    (build / "gui.spec").write_text('hiddenimports=["PySide6.QtWidgets"]\nexcludes=["PySide6", "shiboken6"]\n# PySide6\ncollect_dynamic_libs("shiboken6")\n', encoding="utf-8")
    assert {item["reference"] for item in packaging_blockers(tmp_path)} == {"PySide6.QtWidgets", "shiboken6"}


def test_runtime_and_p0_are_hard_blockers():
    assert gate(default_runtime="qt")[0] == "NO-GO"
    assert gate(p0={"GUI-TEST-001": "PARTIAL"})[0] == "NO-GO"


def test_platform_completeness_is_hard_blocker():
    assert gate(packaged={"windows": "PASS", "linux": "MISSING", "macos": "MISSING"})[0] == "NO-GO"
    assert gate(manual={"windows": "PASS", "linux": "PASS", "macos": "UNVERIFIED"})[0] == "NO-GO"


def test_true_go_fixture():
    assert gate()[0] == "GO"


def test_evidence_schema_shape_is_versioned():
    data = {"schema": "wx-packaged-smoke/1", "commit": SHA, "result": "PASS", "checks": {name: "PASS" for name in PACKAGED_CHECKS}}
    assert data["schema"] and len(data["commit"]) == 40
    assert set(MANUAL_CHECKS) >= {"connection", "shutdown"}

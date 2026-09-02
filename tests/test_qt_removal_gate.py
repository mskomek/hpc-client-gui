import json
import subprocess

import pytest

from scripts.qt_removal_gate import (
    MANUAL_CHECKS,
    PACKAGED_CHECKS,
    dependency_records,
    evaluate_gate,
    git_tracked_files,
    packaging_blockers,
    production_qt_imports,
    read_manual_evidence,
    read_packaged_evidence,
)

SHA = "a" * 40


def git_fixture(tmp_path, files):
    for name, content in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Gate Test"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "fixture"], cwd=tmp_path, check=True, capture_output=True)
    return tmp_path


def gate(**overrides):
    values = {"p0": {"GUI-TEST-001": "COVERED"}, "qt_imports": [], "qt_dependencies": [], "qt_packaging": [], "default_runtime": "wx", "packaged": {p: "PASS" for p in ("windows", "linux", "macos")}, "manual": {p: "PASS" for p in ("windows", "linux", "macos")}, "commit": SHA}
    values.update(overrides)
    return evaluate_gate(**values)


def evidence(path, schema, platform, check_names, **extra):
    data = {"schema": schema, "commit": SHA, "generated_at": "2026-01-01T00:00:00Z", "platform": platform, "architecture": "x86_64", "artifact": "app", "artifact_sha256": "b" * 64, "result": "PASS", "checks": {name: "PASS" for name in check_names}}
    data.update(extra)
    path.write_text(json.dumps(data), encoding="utf-8")


def test_tracked_source_scan_ignores_comments_and_untracked_file(tmp_path):
    root = git_fixture(tmp_path, {"src/hpc_gui/safe.py": '"""PySide6 mention."""\n# import PySide6\n'})
    (root / "src/hpc_gui/local_test.py").write_text("import PySide6\n", encoding="utf-8")
    assert production_qt_imports(root) == []
    tracked = root / "src/hpc_gui/bad.py"
    tracked.write_text("import PySide6.QtWidgets\nfrom PySide6.QtCore import QObject\n", encoding="utf-8")
    subprocess.run(["git", "add", str(tracked)], cwd=root, check=True)
    assert [item["import"] for item in production_qt_imports(root)] == ["PySide6.QtWidgets", "PySide6.QtCore"]


def test_git_tracked_enumeration_rejects_git_failure(tmp_path):
    with pytest.raises(Exception):
        git_tracked_files(tmp_path)


def test_ignored_lock_does_not_contaminate_dependency_scan(tmp_path):
    root = git_fixture(tmp_path, {"pyproject.toml": "dependencies = ['PySide6']\n", "requirements.txt": "PySide6\n", "requirements-release.lock": "PySide6\n"})
    before = dependency_records(root)
    (root / ".gitignore").write_text("uv.lock\n", encoding="utf-8")
    (root / "uv.lock").write_text("PySide6\nshiboken6\n", encoding="utf-8")
    assert dependency_records(root) == before


def test_dependency_family_is_detected_from_release_lock(tmp_path):
    root = git_fixture(tmp_path, {"requirements-release.lock": "PySide6\nPySide6_Addons\nPySide6_Essentials\nshiboken6\n"})
    assert {item["normalized"] for item in dependency_records(root)} == {"pyside6", "pyside6-addons", "pyside6-essentials", "shiboken6"}


def test_ignored_spec_does_not_contaminate_packaging_scan(tmp_path):
    root = git_fixture(tmp_path, {"build/windows/gui.spec": "hiddenimports=['PySide6.QtCore']\n"})
    before = packaging_blockers(root)
    (root / ".gitignore").write_text("build/generated/\n", encoding="utf-8")
    generated = root / "build/generated/copy.spec"
    generated.parent.mkdir(parents=True)
    generated.write_text("hiddenimports=['PySide6.QtWidgets']\n", encoding="utf-8")
    assert packaging_blockers(root) == before


def test_packaging_patterns_and_cli_excludes(tmp_path):
    root = git_fixture(tmp_path, {"build/gui.spec": "hiddenimports = sorted({'PySide6.QtCore'})\nbinaries = collect_dynamic_libs('shiboken6')\nhiddenimports.extend(['PySide6.QtWidgets'])\nAnalysis(hiddenimports=['PySide6.QtGui'])\n", "build/cli.spec": "Analysis(excludes=['PySide6', 'shiboken6'])\n"})
    refs = {item["reference"] for item in packaging_blockers(root)}
    assert refs == {"PySide6.QtCore", "shiboken6", "PySide6.QtWidgets", "PySide6.QtGui"}


def test_evidence_validator_matrix(tmp_path):
    missing = tmp_path / "missing.json"
    assert read_packaged_evidence(missing, "windows", SHA)[0] == "MISSING"
    path = tmp_path / "evidence.json"
    path.write_text("{", encoding="utf-8")
    assert read_packaged_evidence(path, "windows", SHA)[0] == "INVALID"
    evidence(path, "wrong/1", "windows", PACKAGED_CHECKS)
    assert read_packaged_evidence(path, "windows", SHA)[0] == "INVALID"
    evidence(path, "wx-packaged-smoke/1", "windows", PACKAGED_CHECKS, commit="short")
    assert read_packaged_evidence(path, "windows", SHA)[0] == "STALE"
    evidence(path, "wx-packaged-smoke/1", "linux", PACKAGED_CHECKS)
    assert read_packaged_evidence(path, "windows", SHA)[0] == "FAIL"
    for extra in ({"result": "FAIL"}, {"result": "UNVERIFIED"}, {"artifact": ""}, {"artifact_sha256": "1234"}, {"checks": {}}):
        evidence(path, "wx-packaged-smoke/1", "windows", PACKAGED_CHECKS, **extra)
        assert read_packaged_evidence(path, "windows", SHA)[0] != "PASS"
    evidence(path, "wx-packaged-smoke/1", "windows", PACKAGED_CHECKS)
    assert read_packaged_evidence(path, "windows", SHA)[0] == "PASS"


def test_manual_evidence_requires_audit_fields(tmp_path):
    path = tmp_path / "manual.json"
    evidence(path, "wx-manual-parity/1", "windows", MANUAL_CHECKS)
    assert read_manual_evidence(path, "windows", SHA)[0] == "INVALID"
    evidence(path, "wx-manual-parity/1", "windows", MANUAL_CHECKS, tester="", tested_at="bad")
    assert read_manual_evidence(path, "windows", SHA)[0] == "INVALID"
    evidence(path, "wx-manual-parity/1", "windows", MANUAL_CHECKS, tester="manual-win", tested_at="2026-09-02T15:30:00+03:00")
    assert read_manual_evidence(path, "windows", SHA)[0] == "PASS"


def test_gate_requires_platforms_runtime_p0_and_clean_tree():
    assert gate(default_runtime="qt")[0] == "NO-GO"
    assert gate(p0={"GUI-TEST-001": "UNVERIFIED"})[0] == "NO-GO"
    assert gate(packaged={"windows": "PASS", "linux": "MISSING", "macos": "MISSING"})[0] == "NO-GO"
    assert gate(dirty_relevant=["src/hpc_gui/runtime.py"])[0] == "NO-GO"


def test_true_go_fixture():
    assert gate()[0] == "GO"

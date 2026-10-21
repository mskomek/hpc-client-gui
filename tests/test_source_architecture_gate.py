from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import check_source_architecture as architecture  # noqa: E402


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _git_repo(path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Architecture Test"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "architecture@example.invalid"], cwd=path, check=True)
    subprocess.run(["git", "commit", "--allow-empty", "-qm", "baseline"], cwd=path, check=True)


def test_relative_import_resolution_distinguishes_package_and_module() -> None:
    node = ast.ImportFrom(module="_leaf", names=[], level=1)
    assert architecture._resolve_from_module("hpc_gui.jobs", node, True) == "hpc_gui.jobs._leaf"
    assert architecture._resolve_from_module("hpc_gui.jobs.panel", node, False) == "hpc_gui.jobs._leaf"


def test_project_scan_reports_missing_internal_imports_and_cycles(tmp_path: Path) -> None:
    _git_repo(tmp_path)
    _write(tmp_path / "src/hpc_gui/a.py", "from .b import B\nclass A: pass\n")
    _write(tmp_path / "src/hpc_gui/b.py", "from .a import A\nclass B: pass\n")
    _write(tmp_path / "src/hpc_gui/c.py", "from .missing import Missing\n")

    scan = architecture._scan_project(tmp_path)

    assert any("unresolved internal import 'hpc_gui.missing'" in item for item in scan["dependency_errors"])
    assert ["hpc_gui.a", "hpc_gui.b"] in architecture._cycles(scan["graph"])


def test_namespace_package_imports_from_tests_and_scripts_resolve(tmp_path: Path) -> None:
    _git_repo(tmp_path)
    _write(tmp_path / "scripts/checker.py", "def run(): pass\n")
    _write(tmp_path / "tests/test_checker.py", "from scripts import checker\n")

    scan = architecture._scan_project(tmp_path)

    assert scan["dependency_errors"] == []


def test_public_facade_contract_detects_removed_exports() -> None:
    tree = ast.parse("def retained(): pass\nclass Kept: pass\n")
    errors = architecture._api_errors(
        {"trees": {"src/hpc_gui/api.py": tree}},
        {"public_api": {"src/hpc_gui/api.py": ["retained", "Removed", "Kept"]}},
    )
    assert errors == ["src/hpc_gui/api.py: missing public facade symbols: Removed"]


def test_public_symbols_honor_explicit_all_instead_of_imported_names() -> None:
    tree = ast.parse("import os\nfrom typing import Any\ndef build(): pass\n__all__ = ['build']\n")

    assert architecture._public_symbols(tree) == {"build"}


def test_baseline_report_keeps_shared_loc_failure_distinct(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _git_repo(tmp_path)
    _write(tmp_path / "src/hpc_gui/api.py", "def retained(): pass\n")
    _write(
        tmp_path / ".agents-core/.opencode/scripts/validate-source-architecture.py",
        "print('{}')\n",
    )

    def fake_run(root: Path, core: Path, scope: str, base: str) -> dict[str, object]:
        assert scope == "project"
        return {"status": "FAIL", "scope": scope, "source_count": 1, "errors": ["existing LOC debt"], "exit_code": 1}

    monkeypatch.setattr(architecture, "_run_shared_loc", fake_run)
    monkeypatch.chdir(tmp_path)
    code = architecture.main([
        "--mode", "baseline",
        "--core-root", str(tmp_path / ".agents-core"),
        "--json-report", ".tmp/report.json",
        "--markdown-report", ".tmp/report.md",
    ])

    report = json.loads((tmp_path / ".tmp/report.json").read_text(encoding="utf-8"))
    api_contract = json.loads((tmp_path / "docs/architecture/public-api-contracts.json").read_text(encoding="utf-8"))
    assert code == 0
    assert report["status"] == "BASELINE_RECORDED"
    assert report["shared_loc_passed"] is False
    assert (tmp_path / "docs/architecture/source-loc-baseline.json").is_file()
    assert len(api_contract["baseline_commit"]) == 40
    assert api_contract["modules"] == {}

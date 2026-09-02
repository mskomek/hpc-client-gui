"""Produce evidence-based GO/NO-GO output for Qt retirement."""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QT_PREFIXES = ("PySide6", "shiboken6", "QtCore", "QtGui", "QtWidgets", "QtSvg", "QtWeb")


def production_qt_imports(root: Path) -> list[dict[str, object]]:
    found = []
    for path in (root / "src").rglob("*.py"):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            modules = [alias.name for alias in node.names] if isinstance(node, ast.Import) else [node.module or ""] if isinstance(node, ast.ImportFrom) else []
            for module in modules:
                if module.startswith(QT_PREFIXES):
                    found.append({"path": str(path.relative_to(root)), "line": node.lineno, "import": module})
    return found


def evaluate_gate(baseline: str, status: str, pyproject: str, qt_files: list[str] | None = None, *, qt_imports=None, packaging_blockers=None, default_entrypoint_blocker: bool = False, packaged_evidence: bool = False, manual_evidence: bool = False) -> dict[str, object]:
    p0 = set(re.findall(r"\|\s*(GUI-[A-Z]+-\d{3})\s*\|.*?\|\s*P0\s*\|", baseline))
    status_rows = dict(re.findall(r"\|\s*(GUI-[A-Z]+-\d{3})\s*\|\s*([^|]+?)\s*\|", status))
    reasons = [f"P0 not covered: {item}" for item in sorted(p0) if status_rows.get(item, "").strip() != "COVERED"]
    qt_files, qt_imports, packaging_blockers = list(qt_files or []), list(qt_imports or []), list(packaging_blockers or [])
    if qt_files:
        reasons.append(f"Qt-only production files remain: {len(qt_files)}")
    if qt_imports:
        reasons.append(f"Qt production imports remain: {len(qt_imports)}")
    dependencies = [line.strip() for line in pyproject.splitlines() if any(name in line for name in ("PySide6", "shiboken6"))]
    if dependencies:
        reasons.append("Qt runtime dependency remains declared")
    if packaging_blockers:
        reasons.append(f"Qt packaging blockers remain: {len(packaging_blockers)}")
    if default_entrypoint_blocker:
        reasons.append("default GUI entrypoint still launches Qt")
    if not packaged_evidence:
        reasons.append("packaged wx smoke evidence is missing")
    if not manual_evidence:
        reasons.append("mandatory manual wx evidence is missing")
    return {"schema": "qt-removal-gate/2", "decision": "GO" if not reasons else "NO-GO", "reasons": reasons, "qt_dependencies": dependencies, "qt_files": qt_files, "qt_imports": qt_imports, "qt_packaging": packaging_blockers, "packaged_evidence": packaged_evidence, "manual_evidence": manual_evidence}


def main() -> int:
    qt_imports = production_qt_imports(ROOT)
    qt_files = sorted({str(item["path"]) for item in qt_imports})
    packaging_blockers = []
    for path in (ROOT / "build").rglob("*.spec"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if any(name in text for name in QT_PREFIXES):
            packaging_blockers.append(str(path.relative_to(ROOT)))
    manual_path = ROOT / "docs" / "v2" / "manual-results"
    report = evaluate_gate((ROOT / "docs/v2/GUI_FEATURE_PARITY_BASELINE.md").read_text(encoding="utf-8"), (ROOT / "docs/v2/V2_PARITY_STATUS.md").read_text(encoding="utf-8"), (ROOT / "pyproject.toml").read_text(encoding="utf-8"), qt_files, qt_imports=qt_imports, packaging_blockers=packaging_blockers, default_entrypoint_blocker="from hpc_gui.app import main" in (ROOT / "src/hpc_gui/__main__.py").read_text(encoding="utf-8"), packaged_evidence=(ROOT / "build/audit/wx-packaged-smoke.json").is_file(), manual_evidence=manual_path.is_dir() and any(manual_path.glob("*.md")))
    print(json.dumps(report, sort_keys=True))
    return 0 if report["decision"] == "GO" else 2


if __name__ == "__main__":
    raise SystemExit(main())

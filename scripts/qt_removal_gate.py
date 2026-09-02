"""Produce evidence-based GO/NO-GO output for Qt retirement."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def evaluate_gate(baseline: str, status: str, pyproject: str, qt_files: list[str] | None = None) -> dict[str, object]:
    p0 = set(re.findall(r"\|\s*(GUI-[A-Z]+-\d{3})\s*\|.*?\|\s*P0\s*\|", baseline))
    status_rows = dict(re.findall(r"\|\s*(GUI-[A-Z]+-\d{3})\s*\|\s*([^|]+?)\s*\|", status))
    reasons = [f"P0 not covered: {item}" for item in sorted(p0) if status_rows.get(item, "").strip() != "COVERED"]
    dependencies = [line.strip() for line in pyproject.splitlines() if "PySide6" in line]
    qt_files = list(qt_files or [])
    if qt_files:
        reasons.append(f"Qt-only production files remain: {len(qt_files)}")
    return {"schema": "qt-removal-gate/1", "decision": "GO" if not reasons else "NO-GO", "reasons": reasons, "qt_dependencies": dependencies, "qt_files": qt_files}


def main() -> int:
    qt_files = [str(path.relative_to(ROOT)) for path in (ROOT / "src").rglob("*.py") if "PySide6" in path.read_text(encoding="utf-8", errors="ignore")]
    report = evaluate_gate(
        (ROOT / "docs/v2/GUI_FEATURE_PARITY_BASELINE.md").read_text(encoding="utf-8"),
        (ROOT / "docs/v2/V2_PARITY_STATUS.md").read_text(encoding="utf-8"),
        (ROOT / "pyproject.toml").read_text(encoding="utf-8"),
        qt_files,
    )
    print(json.dumps(report, sort_keys=True))
    return 0 if report["decision"] == "GO" else 2


if __name__ == "__main__":
    raise SystemExit(main())

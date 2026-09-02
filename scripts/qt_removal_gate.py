"""Produce evidence-based GO/NO-GO output for Qt retirement."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def evaluate_gate(baseline: str, status: str, pyproject: str) -> dict[str, object]:
    p0 = set(re.findall(r"\|\s*(GUI-[A-Z]+-\d{3})\s*\|.*?\|\s*P0\s*\|", baseline))
    status_rows = dict(re.findall(r"\|\s*(GUI-[A-Z]+-\d{3})\s*\|\s*([^|]+?)\s*\|", status))
    reasons = [f"P0 not covered: {item}" for item in sorted(p0) if status_rows.get(item, "").strip() != "COVERED"]
    dependencies = [line.strip() for line in pyproject.splitlines() if "PySide6" in line]
    return {"schema": "qt-removal-gate/1", "decision": "GO" if not reasons else "NO-GO", "reasons": reasons, "qt_dependencies": dependencies}


def main() -> int:
    report = evaluate_gate(
        (ROOT / "docs/v2/GUI_FEATURE_PARITY_BASELINE.md").read_text(encoding="utf-8"),
        (ROOT / "docs/v2/V2_PARITY_STATUS.md").read_text(encoding="utf-8"),
        (ROOT / "pyproject.toml").read_text(encoding="utf-8"),
    )
    print(json.dumps(report, sort_keys=True))
    return 0 if report["decision"] == "GO" else 2


if __name__ == "__main__":
    raise SystemExit(main())

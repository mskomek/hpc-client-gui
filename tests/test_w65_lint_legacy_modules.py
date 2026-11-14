"""W65 LINT-013: the legacy rule prototypes stay out of the production path."""
from __future__ import annotations

from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
LEGACY = SRC / "hpc_gui" / "plugins" / "openfoam_lint"
LEGACY_MARKER = "Library-only: no production module imports this file."


def test_no_production_module_imports_the_legacy_rule_files():
    offenders = []
    for path in SRC.rglob("*.py"):
        if path.parent == LEGACY and path.name in {"rules_cross.py", "rules_physics.py"}:
            continue
        text = path.read_text(encoding="utf-8")
        if "rules_cross" in text or "rules_physics" in text:
            offenders.append(path.relative_to(SRC).as_posix())

    assert offenders == []


def test_legacy_modules_declare_themselves():
    for name in ("rules_cross.py", "rules_physics.py"):
        text = (LEGACY / name).read_text(encoding="utf-8")
        assert LEGACY_MARKER in text

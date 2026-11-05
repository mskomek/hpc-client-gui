"""Rule catalog and report serialization."""
from __future__ import annotations

import json
from dataclasses import dataclass

from hpc_gui.openfoam_core import Diagnostic
from .rules_dictionary import RULES


@dataclass(frozen=True, slots=True)
class LintResult:
    diagnostics: tuple[Diagnostic, ...]
    files_checked: tuple[str, ...]
    level: str = "static"
    edition: str = "OpenFOAM.com / ESI"
    version: str = "v2312"

    @property
    def errors(self) -> int:
        return sum(item.severity == "error" for item in self.diagnostics)

    @property
    def warnings(self) -> int:
        return sum(item.severity == "warning" for item in self.diagnostics)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "level": self.level,
            "verification_levels": sorted({item.verification_level for item in self.diagnostics}) or ["static"],
            "edition": self.edition,
            "version": self.version,
            "files_checked": list(self.files_checked),
            "summary": {"errors": self.errors, "warnings": self.warnings, "findings": len(self.diagnostics)},
            "diagnostics": [item.to_dict() for item in self.diagnostics],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    def to_markdown(self) -> str:
        lines = [f"# OpenFOAM case lint — {self.version}", "", f"Files checked: {len(self.files_checked)}", "", "| Verification | Severity | Rule | File:line | Finding |", "|---|---|---|---|---|"]
        for item in self.diagnostics:
            lines.append(f"| {item.verification_level} | {item.severity} | {item.rule_id} | {item.path}:{item.line} | {item.message} |")
        if not self.diagnostics:
            lines.append("| static | info | — | — | No findings from the enabled static rules. |")
        lines += ["", "Static lint does not run OpenFOAM or prove physical correctness. Contextual findings use only the selected case files and filesystem metadata. Runtime findings are not produced by this version."]
        return "\n".join(lines) + "\n"


def rule_catalog() -> dict[str, dict[str, str]]:
    return {key: dict(value) for key, value in RULES.items()}

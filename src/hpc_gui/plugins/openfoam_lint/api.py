"""Linter core: severity-tagged diagnostics over parsed dictionaries.

Preserves 0.1.0 rule-ID prefixes. Static only: never evaluates dynamic
directives. Each rule returns diagnostics with file/line/column anchors.
"""

from __future__ import annotations

from dataclasses import dataclass

from hpc_gui.openfoam_core.lexer import contains_executable_directive, lex
from hpc_gui.openfoam_core.parser import parse_text


@dataclass(frozen=True)
class Diagnostic:
    rule: str
    severity: str  # error | warning | info
    certainty: str  # definite | heuristic
    file: str
    line: int
    column: int
    message: str
    fix_preview: str = ""


def lint_text(relpath: str, text: str) -> list[Diagnostic]:
    diags: list[Diagnostic] = []
    tokens = lex(text)
    if contains_executable_directive(tokens):
        tok = next(t for t in tokens if t.kind == "DIRECTIVE")
        diags.append(Diagnostic("OF-SEC-001", "warning", "definite", relpath,
                                tok.line, tok.column,
                                "executable directive present; static lint does not evaluate it"))
    if "#include" in text and (".." in text or "/etc/" in text):
        diags.append(Diagnostic("OF-SEC-002", "error", "heuristic", relpath, 1, 1,
                                "include path escapes case root or reaches absolute path"))
    parsed = parse_text(text)
    for issue in parsed.issues:
        diags.append(Diagnostic("OF-DICT-001", "error", "definite", relpath,
                                issue.line, issue.column, issue.message))
    if "FoamFile" not in parsed.entries and relpath.endswith(("Dict", "Properties")):
        diags.append(Diagnostic("OF-DICT-002", "warning", "definite", relpath, 1, 1,
                                "missing FoamFile header"))
    for inc in parsed.includes:
        if inc.lower() not in ("#include", "#includeetc", "#includefunc"):
            diags.append(Diagnostic("OF-DICT-003", "warning", "heuristic", relpath, 1, 1,
                                    f"unknown directive '{inc}' preserved raw"))
    return diags


def rule_catalog() -> list[dict]:
    return [
        {"id": "OF-DICT-001", "family": "OF-DICT", "severity": "error"},
        {"id": "OF-DICT-002", "family": "OF-DICT", "severity": "warning"},
        {"id": "OF-DICT-003", "family": "OF-DICT", "severity": "warning"},
        {"id": "OF-SEC-001", "family": "OF-SEC", "severity": "warning"},
        {"id": "OF-SEC-002", "family": "OF-SEC", "severity": "error"},
        {"id": "OF-CASE-010", "family": "OF-CASE", "severity": "error"},
        {"id": "OF-MESH-010", "family": "OF-MESH", "severity": "error"},
        {"id": "OF-BC-010", "family": "OF-BC", "severity": "error"},
        {"id": "OF-CTRL-010", "family": "OF-CTRL", "severity": "error"},
        {"id": "OF-SOLVER-010", "family": "OF-SOLVER", "severity": "error"},
        {"id": "OF-CROSS-010", "family": "OF-CROSS", "severity": "error"},
        {"id": "OF-PAR-010", "family": "OF-PAR", "severity": "error"},
        {"id": "OF-HPC-010", "family": "OF-HPC", "severity": "warning"},
        {"id": "OF-WF-010", "family": "OF-CROSS", "severity": "error"},
        {"id": "OF-PHYS-010", "family": "OF-SOLVER", "severity": "error"},
        {"id": "OF-NUM-010", "family": "OF-CTRL", "severity": "error"},
    ]

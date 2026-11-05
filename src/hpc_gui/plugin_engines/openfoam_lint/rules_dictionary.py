"""Static dictionary rules. No solver, include, #calc, #eval, or codeStream is executed."""
from __future__ import annotations

from hpc_gui.openfoam_core import Diagnostic, ParsedDictionary, SOURCE_DOCS, Token, parse_dictionary

RULES = {
    "OF-DICT-001": {"title": "Dictionary structure", "severity": "error", "confidence": "structural", "source": SOURCE_DOCS},
    "OF-DICT-002": {"title": "Duplicate key", "severity": "warning", "confidence": "structural", "source": SOURCE_DOCS},
    "OF-DICT-003": {"title": "FoamFile header", "severity": "warning", "confidence": "contextual", "source": SOURCE_DOCS},
    "OF-DICT-004": {"title": "Dimension set", "severity": "warning", "confidence": "structural", "source": SOURCE_DOCS},
    "OF-SEC-001": {"title": "Dynamic directive retained", "severity": "info", "confidence": "certain", "source": SOURCE_DOCS},
    "OF-SEC-002": {"title": "Unsafe include path", "severity": "warning", "confidence": "structural", "source": SOURCE_DOCS},
    "OF-HPC-001": {"title": "Nonportable path", "severity": "warning", "confidence": "heuristic", "source": SOURCE_DOCS},
}


def _header_checks(parsed: ParsedDictionary, path: str) -> list[Diagnostic]:
    header = {entry.key: entry for entry in parsed.entries if entry.scope == ("FoamFile",)}
    if not header:
        return []
    required = ("version", "format", "class", "object")
    missing = [key for key in required if key not in header]
    if not missing:
        return []
    first = next(iter(header.values()))
    return [Diagnostic(
        "OF-DICT-003", "warning", "contextual", path, first.line, first.column,
        "FoamFile header is missing " + ", ".join(missing) + ".",
        "Check the header against the dictionary type and OpenFOAM.com v2312 documentation.",
        SOURCE_DOCS,
    )]


def _dimension_checks(tokens: tuple[Token, ...], path: str) -> list[Diagnostic]:
    result: list[Diagnostic] = []
    index = 0
    while index < len(tokens):
        if tokens[index].value != "[":
            index += 1
            continue
        opening = tokens[index]
        values: list[str] = []
        cursor = index + 1
        while cursor < len(tokens) and tokens[cursor].value != "]":
            if tokens[cursor].kind != "punct":
                values.append(tokens[cursor].value)
            cursor += 1
        valid = len(values) == 7 and all(value.lstrip("+-").isdigit() for value in values)
        if cursor >= len(tokens) or not valid:
            result.append(Diagnostic(
                "OF-DICT-004", "warning", "structural", path, opening.line, opening.column,
                "Dimension set is not seven integer exponents.",
                "Review the dimension vector; static lint does not infer physical units.", SOURCE_DOCS,
            ))
        index = cursor + 1
    return result


def _path_checks(parsed: ParsedDictionary, path: str) -> list[Diagnostic]:
    result: list[Diagnostic] = []
    tokens = parsed.tokens
    for index, token in enumerate(tokens):
        if token.kind == "directive" and token.value in {"#include", "#includeEtc"}:
            target = tokens[index + 1] if index + 1 < len(tokens) else None
            if target and target.kind == "string":
                value = target.value.strip('"\'')
                normalized = value.replace("\\", "/")
                parts = normalized.split("/")
                if normalized.startswith("/") or (len(normalized) > 1 and normalized[1] == ":") or ".." in parts:
                    result.append(Diagnostic(
                        "OF-SEC-002", "warning", "structural", path, token.line, token.column,
                        "Include path is absolute or escapes the case directory.",
                        "Use a case-relative include and inspect symlinks before contextual resolution.", SOURCE_DOCS,
                    ))
        if token.kind == "string" and ("\\" in token.value or (len(token.value) > 2 and token.value[1:3] == ":\\")):
            result.append(Diagnostic(
                "OF-HPC-001", "warning", "heuristic", path, token.line, token.column,
                "String contains a Windows-style path that may not work on Linux HPC nodes.",
                "Use a profile-relative POSIX path when the dictionary expects a file path.", SOURCE_DOCS,
            ))
    return result


def lint_dictionary(text: str, *, path: str) -> tuple[ParsedDictionary, tuple[Diagnostic, ...]]:
    parsed = parse_dictionary(text, path=path)
    findings = [*parsed.diagnostics, *_header_checks(parsed, path), *_dimension_checks(parsed.tokens, path), *_path_checks(parsed, path)]
    return parsed, tuple(findings)

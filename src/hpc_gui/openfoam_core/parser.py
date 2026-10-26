"""Legacy dict-shaped view over the single static engine (W65 LINT-COMPAT).

``parse_text`` preserves the historical ``parser.ParsedDictionary``
contract (``entries`` dict, ``order``, ``spans``, ``issues``,
``has_executable_directive``, ``includes``) for API1/API2 clients. It is a
deliberately small projection over ``document.parse_dictionary`` using the
same tokenizer and the same never-evaluate security posture, never a
parallel parser. New code must use the rich ``document`` contract via the
``hpc_gui.openfoam_core`` facade.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from hpc_gui.openfoam_core.document import parse_dictionary as _parse_rich
from hpc_gui.openfoam_core.limits import SOURCE_DOCS as SOURCE_DOCS

__all__ = ["ParseIssue", "ParsedDictionary", "SOURCE_DOCS", "parse_text"]


@dataclass
class ParseIssue:
    message: str
    line: int
    column: int


@dataclass
class ParsedDictionary:
    entries: dict = field(default_factory=dict)
    order: list[str] = field(default_factory=list)
    spans: dict = field(default_factory=dict)
    issues: list[ParseIssue] = field(default_factory=list)
    has_executable_directive: bool = False
    includes: list[str] = field(default_factory=list)


def parse_text(text: str) -> ParsedDictionary:
    if not isinstance(text, str):
        raise TypeError("dictionary text must be str")
    rich = _parse_rich(text)
    parsed = ParsedDictionary()
    for token in rich.tokens:
        if token.kind == "directive" and token.value.lower() in (
            "#codestream", "#calc", "#eval",
        ):
            parsed.has_executable_directive = True
        if token.kind == "directive" and token.value.lower() in (
            "#include", "#includeetc", "#includefunc",
        ):
            parsed.includes.append(token.value)
    children: dict[str, list[str]] = {}
    for entry in rich.entries:
        if entry.scope:
            children.setdefault(entry.scope[0], []).append(
                f"{entry.key} {entry.value}".strip()
            )
    for entry in rich.entries:
        if entry.scope:
            continue
        if entry.key not in parsed.entries:
            parsed.order.append(entry.key)
        if entry.is_dictionary:
            inner = "; ".join(children.get(entry.key, []))
            parsed.entries[entry.key] = {"__block__": inner}
        else:
            parsed.entries[entry.key] = entry.value
        parsed.spans[entry.key] = (entry.line, entry.column, entry.end_line, entry.end_column)
    for diagnostic in rich.diagnostics:
        if diagnostic.rule_id in ("OF-DICT-001", "OF-DICT-002"):
            parsed.issues.append(
                ParseIssue(diagnostic.message, diagnostic.line, diagnostic.column)
            )
    return parsed

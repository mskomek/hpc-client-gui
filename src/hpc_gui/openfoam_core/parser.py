"""Minimal OpenFOAM dictionary parser (W65 BASE-001).

Builds a nested node tree preserving source spans. Unknown or dynamic
constructs (``#codeStream`` blocks, ``$variables``, regex patch names)
are preserved as raw entries and never evaluated.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from hpc_gui.openfoam_core.lexer import LexToken, lex


@dataclass
class ParseIssue:
    message: str
    line: int
    column: int


@dataclass
class ParsedDictionary:
    entries: dict = field(default_factory=dict)  # key -> value | dict | list | {"__raw__": text}
    order: list[str] = field(default_factory=list)
    spans: dict = field(default_factory=dict)  # key -> (start_line, start_col, end_line, end_col)
    issues: list[ParseIssue] = field(default_factory=list)
    has_executable_directive: bool = False
    includes: list[str] = field(default_factory=list)


def parse_text(text: str) -> ParsedDictionary:
    tokens = lex(text)
    parsed = ParsedDictionary()
    for tok in tokens:
        if tok.kind == "DIRECTIVE" and tok.text.lower() in ("#codestream", "#calc", "#eval"):
            parsed.has_executable_directive = True
        if tok.kind == "DIRECTIVE" and tok.text.lower() in ("#include", "#includeetc", "#includefunc"):
            parsed.includes.append(tok.text)
    # Structural parse: sequence of `key value... ;` or `key { ... }`.
    idx = 0
    n = len(tokens)
    while idx < n:
        tok = tokens[idx]
        if tok.kind in ("COMMENT", "DIRECTIVE", "SEMI", "RBRACE", "RPAREN"):
            idx += 1
            continue
        if tok.kind in ("LBRACE", "LPAREN"):
            parsed.issues.append(ParseIssue("unexpected block open", tok.line, tok.column))
            idx += 1
            continue
        key = tok.text
        key_line, key_col = tok.line, tok.column
        idx += 1
        # Skip FoamFile-style header words already consumed as key; gather value tokens.
        values: list[LexToken] = []
        depth_brace = 0
        depth_paren = 0
        closed = False
        while idx < n:
            t = tokens[idx]
            if t.kind == "LBRACE":
                depth_brace += 1
                values.append(t)
            elif t.kind == "RBRACE":
                if depth_brace == 0:
                    break
                depth_brace -= 1
                values.append(t)
            elif t.kind == "LPAREN":
                depth_paren += 1
                values.append(t)
            elif t.kind == "RPAREN":
                if depth_paren == 0 and depth_brace == 0:
                    values.append(t)
                    idx += 1
                    continue
                depth_paren = max(0, depth_paren - 1)
                values.append(t)
            elif t.kind == "SEMI" and depth_brace == 0 and depth_paren == 0:
                closed = True
                end_line, end_col = t.line, t.column
                idx += 1
                break
            elif t.kind == "LBRACE" and False:  # pragma: no cover - clarity
                pass
            else:
                values.append(t)
            idx += 1
            if depth_brace == 0 and values and values[-1].kind == "RBRACE":
                # `key { ... }` block without trailing semicolon is legal.
                closed = True
                end_line, end_col = values[-1].line, values[-1].column
                break
        else:
            end_line, end_col = key_line, key_col
        if not closed and not values:
            continue
        if not closed:
            parsed.issues.append(ParseIssue(f"entry '{key}' missing terminating ';'", key_line, key_col))
            end_line, end_col = (values[-1].line, values[-1].column) if values else (key_line, key_col)
        if key not in parsed.entries:
            parsed.order.append(key)
        parsed.entries[key] = _materialize(values)
        parsed.spans[key] = (key_line, key_col, end_line, end_col)
    return parsed


def _materialize(values: list[LexToken]):
    if not values:
        return ""
    if len(values) == 1 and values[0].kind in ("WORD", "NUMBER", "STRING"):
        return values[0].text
    if values[0].kind == "LBRACE" and values[-1].kind == "RBRACE":
        inner = " ".join(v.text for v in values[1:-1] if v.kind != "COMMENT")
        return {"__block__": inner}
    if values[0].kind == "LPAREN":
        return [v.text for v in values if v.kind not in ("LPAREN", "RPAREN", "COMMENT")]
    return " ".join(v.text for v in values if v.kind != "COMMENT")

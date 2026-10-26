"""Single static OpenFOAM dictionary engine (W65 LINT-COMPAT).

One real tokenizer (``lexer.lex``) feeds one structural pass. Directives,
includes, ``$variables`` and ``#codeStream``/``#calc``/``#eval`` blocks are
tokenized but never expanded or evaluated; they are carried as opaque
tokens. The legacy ``parser.parse_text`` dict view is a thin projection
over this engine (see ``parser.py``), never a parallel implementation.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from hpc_gui.openfoam_core.lexer import lex
from hpc_gui.openfoam_core.limits import SOURCE_DOCS

_EXECUTABLE = ("#codestream", "#calc", "#eval")
_INCLUDE = ("#include", "#includeetc", "#includefunc")


@dataclass(frozen=True, slots=True)
class Diagnostic:
    """One static finding anchored to a file position."""

    rule_id: str
    severity: str
    confidence: str
    path: str
    line: int
    column: int
    message: str
    suggested_fix: str = ""
    source_url: str = SOURCE_DOCS
    verification_level: str = "static"

    def to_dict(self) -> dict[str, object]:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "confidence": self.confidence,
            "path": self.path,
            "line": self.line,
            "column": self.column,
            "message": self.message,
            "suggested_fix": self.suggested_fix,
            "source_url": self.source_url,
            "verification_level": self.verification_level,
        }


@dataclass(frozen=True, slots=True)
class Token:
    """One lexical unit with ``directive/string/atom/punct`` kind."""

    kind: str
    value: str
    line: int
    column: int
    offset: int = 0
    end: int = 0


@dataclass(frozen=True, slots=True)
class Entry:
    """One ``key value... ;`` or ``key { ... }`` dictionary entry."""

    key: str
    scope: tuple[str, ...] = ()
    line: int = 1
    column: int = 1
    end_line: int = 1
    end_column: int = 1
    value: str = ""
    value_tokens: tuple[Token, ...] = ()
    is_dictionary: bool = False
    dynamic: bool = False
    value_start: int = 0
    value_end: int = 0

    @property
    def qualified_key(self) -> str:
        return "/".join((*self.scope, self.key))


@dataclass
class ParsedDictionary:
    """Rich static parse: entries, tokens and structural diagnostics."""

    entries: list[Entry] = field(default_factory=list)
    tokens: tuple[Token, ...] = ()
    diagnostics: tuple[Diagnostic, ...] = ()
    source: str = ""
    path: str = ""

    def find(self, key: str, scope: tuple[str, ...] = ()) -> list[Entry]:
        return [e for e in self.entries if e.key == key and e.scope == tuple(scope)]

    def value(self, key: str, scope: tuple[str, ...] = ()) -> str | None:
        for entry in self.entries:
            if entry.key == key and entry.scope == tuple(scope):
                return entry.value
        return None

    def replace_scalar(self, key: str, value: str, scope: tuple[str, ...] = ()) -> str:
        matches = self.find(key, scope)
        if len(matches) != 1:
            raise ValueError(f"expected one static entry for {key!r}")
        entry = matches[0]
        if entry.is_dictionary or entry.dynamic or not entry.value_tokens:
            raise ValueError(f"entry {key!r} is not a static scalar")
        if not isinstance(value, str) or not value:
            raise ValueError("replacement value must be non-empty text")
        return self.source[: entry.value_start] + value + self.source[entry.value_end :]

    def replace_numeric_components(
        self, key: str, values: tuple[str, ...] | list[str], scope: tuple[str, ...] = ()
    ) -> str:
        matches = self.find(key, scope)
        if len(matches) != 1:
            raise ValueError(f"expected one static entry for {key!r}")
        entry = matches[0]
        if entry.is_dictionary or entry.dynamic:
            raise ValueError(f"entry {key!r} is not statically editable")
        tokens = list(entry.value_tokens)
        try:
            opening = next(i for i, t in enumerate(tokens) if t.value == "(")
            closing = next(i for i in range(len(tokens) - 1, -1, -1) if tokens[i].value == ")")
        except StopIteration as exc:
            raise ValueError(f"entry {key!r} has no numeric component list") from exc
        if closing <= opening:
            raise ValueError(f"entry {key!r} has no numeric component list")
        inner = [t for t in tokens[opening + 1 : closing] if t.kind == "atom"]
        if len(inner) != len(values) or not inner:
            raise ValueError(f"entry {key!r} expects {len(inner)} numeric components")
        replacement = "(" + " ".join(values) + ")"
        return self.source[: tokens[opening].offset] + replacement + self.source[tokens[closing].end :]


def _offsets(text: str) -> list[int]:
    starts = [0]
    for index, char in enumerate(text):
        if char == "\n":
            starts.append(index + 1)
    return starts


def _rich_tokens(text: str) -> list[Token]:
    starts = _offsets(text)
    rich: list[Token] = []

    def offset_of(line: int, column: int) -> int:
        if 1 <= line <= len(starts):
            return starts[line - 1] + column - 1
        return len(text)

    for tok in lex(text):
        if tok.kind == "DIRECTIVE":
            kind = "directive"
        elif tok.kind == "STRING":
            kind = "string"
        elif tok.kind in ("WORD", "NUMBER"):
            kind = "atom"
        elif tok.kind == "COMMENT":
            kind = "comment"
        else:
            kind = "punct"
        start = offset_of(tok.line, tok.column)
        rich.append(Token(kind, tok.text, tok.line, tok.column, start, start + len(tok.text)))
    return rich


def _skip_balanced(tokens: list[Token], pos: int) -> int:
    depth = 0
    while pos < len(tokens):
        tok = tokens[pos]
        if tok.kind == "punct" and tok.value == "{":
            depth += 1
        elif tok.kind == "punct" and tok.value == "}":
            depth -= 1
            if depth <= 0:
                return pos + 1
        pos += 1
    return pos


def parse_dictionary(text: str, *, path: str = "<memory>") -> ParsedDictionary:
    """Parse one dictionary without expanding includes or directives."""
    if not isinstance(text, str):
        raise TypeError("dictionary text must be str")
    tokens = _rich_tokens(text)
    entries: list[Entry] = []
    diagnostics: list[Diagnostic] = []
    seen: dict[tuple[tuple[str, ...], str], Entry] = {}
    label = str(path)

    def duplicate(scope: tuple[str, ...], entry: Entry) -> None:
        previous = seen.get((scope, entry.key))
        if previous is not None:
            diagnostics.append(Diagnostic(
                "OF-DICT-002", "warning", "structural", label,
                entry.line, entry.column,
                f"Duplicate key {entry.key!r} in the same scope.",
                "Keep a single entry for this key or split the dictionary.",
            ))
        else:
            seen[(scope, entry.key)] = entry

    total = len(tokens)

    def parse_block(pos: int, scope: tuple[str, ...]) -> int:
        nonlocal entries
        while pos < total:
            tok = tokens[pos]
            if tok.kind == "comment":
                pos += 1
                continue
            if tok.kind == "directive":
                lowered = tok.value.lower()
                if lowered in _EXECUTABLE:
                    diagnostics.append(Diagnostic(
                        "OF-SEC-001", "info", "certain", label,
                        tok.line, tok.column,
                        f"Dynamic directive {tok.value!r} is retained without evaluation.",
                        "Static lint never executes this directive; verify it manually.",
                    ))
                pos += 1
                if pos < total and tokens[pos].kind == "string":
                    pos += 1
                if pos < total and tokens[pos].kind == "punct" and tokens[pos].value == "{":
                    pos = _skip_balanced(tokens, pos)
                continue
            if tok.kind == "punct" and tok.value == "}":
                if scope:
                    return pos
                diagnostics.append(Diagnostic(
                    "OF-DICT-001", "error", "structural", label,
                    tok.line, tok.column, "Unexpected closing brace.",
                    "Check brace balance; static lint does not evaluate blocks.",
                ))
                pos += 1
                continue
            if tok.kind == "punct":
                if tok.value == ";":
                    pos += 1
                    continue
                if tok.value == "{":
                    diagnostics.append(Diagnostic(
                        "OF-DICT-001", "error", "structural", label,
                        tok.line, tok.column, "Unexpected block open.",
                        "Check brace balance; static lint does not evaluate blocks.",
                    ))
                    pos = _skip_balanced(tokens, pos)
                    continue
                pos += 1
                continue
            if tok.kind in ("atom", "string"):
                key = tok.value.strip("\"'") if tok.kind == "string" else tok.value
                key_line, key_col = tok.line, tok.column
                pos += 1
                while pos < total and tokens[pos].kind == "comment":
                    pos += 1
                if pos < total and tokens[pos].kind == "punct" and tokens[pos].value == "{":
                    opening = tokens[pos]
                    inner = parse_block(pos + 1, scope + (key,))
                    closing = tokens[inner] if inner < total else opening
                    entry = Entry(
                        key=key, scope=scope, line=key_line, column=key_col,
                        end_line=closing.line, end_column=closing.column,
                        value="", value_tokens=(), is_dictionary=True,
                        dynamic=False, value_start=opening.offset, value_end=closing.end,
                    )
                    entries.append(entry)
                    duplicate(scope, entry)
                    pos = inner + 1 if inner < total else inner
                    if pos < total and tokens[pos].kind == "punct" and tokens[pos].value == ";":
                        pos += 1
                    continue
                vals: list[Token] = []
                depth_paren = 0
                depth_brace = 0
                closed = False
                end_tok = tok
                while pos < total:
                    item = tokens[pos]
                    if item.kind == "comment":
                        pos += 1
                        continue
                    if item.kind == "directive":
                        break
                    if item.kind == "punct" and item.value == ";" and not depth_paren and not depth_brace:
                        closed = True
                        end_tok = item
                        pos += 1
                        break
                    if item.kind == "punct" and item.value == "}" and not depth_paren and not depth_brace:
                        break
                    if item.kind == "punct" and item.value == "(":
                        depth_paren += 1
                    elif item.kind == "punct" and item.value == ")":
                        depth_paren = max(0, depth_paren - 1)
                    elif item.kind == "punct" and item.value == "{":
                        depth_brace += 1
                    elif item.kind == "punct" and item.value == "}":
                        depth_brace = max(0, depth_brace - 1)
                    vals.append(item)
                    pos += 1
                if not vals and not closed:
                    continue
                if not closed:
                    diagnostics.append(Diagnostic(
                        "OF-DICT-001", "error", "structural", label,
                        key_line, key_col,
                        f"Entry {key!r} is missing its terminating ';'.",
                        "Terminate the entry with ';' or close the enclosing block.",
                    ))
                    end_tok = vals[-1] if vals else tok
                dynamic = any("$" in item.value for item in vals if item.kind == "atom")
                value = " ".join(item.value for item in vals if item.kind != "comment")
                entry = Entry(
                    key=key, scope=scope, line=key_line, column=key_col,
                    end_line=end_tok.line, end_column=end_tok.column,
                    value=value, value_tokens=tuple(vals),
                    is_dictionary=False, dynamic=dynamic,
                    value_start=vals[0].offset if vals else tok.end,
                    value_end=vals[-1].end if vals else tok.end,
                )
                entries.append(entry)
                duplicate(scope, entry)
                continue
            pos += 1
        return pos

    parse_block(0, ())
    public_tokens = tuple(tok for tok in tokens if tok.kind != "comment")
    return ParsedDictionary(
        entries=entries, tokens=public_tokens,
        diagnostics=tuple(diagnostics), source=text, path=label,
    )

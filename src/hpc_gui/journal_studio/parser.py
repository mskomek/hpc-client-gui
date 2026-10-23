"""Conservative Fluent journal tokenizer; it never evaluates journal code."""

from __future__ import annotations

from bisect import bisect_right
import re

from hpc_gui.journal_studio.models import JournalBlock, JournalDiagnostic, ParsedJournal


MAX_SOURCE_CHARACTERS = 64 * 1024 * 1024
_TUI_PATH = re.compile(r"^\s*(/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*)(?=\s|$)")


def _line_end(source: str, position: int) -> int:
    newline = source.find("\n", position)
    return len(source) if newline < 0 else newline + 1


def _line_starts(source: str) -> list[int]:
    starts = [0]
    starts.extend(index + 1 for index, char in enumerate(source) if char == "\n")
    return starts


def _scheme_start(line: str) -> bool:
    return line.lstrip().startswith("(")


def _tui_path(line: str) -> str | None:
    match = _TUI_PATH.match(line)
    return match.group(1) if match else None


def _scheme_end(source: str, start: int) -> tuple[int, bool, bool]:
    depth = 0
    in_string = False
    escaped = False
    line_comment = False
    block_comment = 0
    saw_open = False
    unclosed_quote = False
    position = start

    while position < len(source):
        char = source[position]
        pair = source[position : position + 2]
        if line_comment:
            if char == "\n":
                line_comment = False
            position += 1
            continue
        if block_comment:
            if pair == "#|":
                block_comment += 1
                position += 2
            elif pair == "|#":
                block_comment -= 1
                position += 2
            else:
                position += 1
            continue
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            position += 1
            continue
        if pair == "#|":
            block_comment = 1
            position += 2
            continue
        if char == ";":
            line_comment = True
            position += 1
            continue
        if char == '"':
            in_string = True
            position += 1
            continue
        if char == "(":
            saw_open = True
            depth += 1
        elif char == ")" and saw_open:
            depth -= 1
            if depth == 0:
                return position + 1, False, False
        position += 1

    unclosed_quote = in_string
    return len(source), True, unclosed_quote


def _block_comment_end(source: str, start: int) -> tuple[int, bool]:
    depth = 0
    position = start
    while position < len(source):
        pair = source[position : position + 2]
        if pair == "#|":
            depth += 1
            position += 2
        elif pair == "|#":
            depth -= 1
            position += 2
            if depth == 0:
                return position, False
        else:
            position += 1
    return len(source), True


def _unclosed_tui_quote(text: str) -> bool:
    in_quote = False
    escaped = False
    for char in text:
        if char == "\n" and not in_quote:
            continue
        if escaped:
            escaped = False
        elif char == "\\" and in_quote:
            escaped = True
        elif char == '"':
            in_quote = not in_quote
    return in_quote


def parse_journal(source: str, *, known_command_paths: frozenset[str] = frozenset()) -> ParsedJournal:
    """Split source into exact contiguous spans and conservative diagnostics."""
    if len(source) > MAX_SOURCE_CHARACTERS:
        raise ValueError(f"journal exceeds the {MAX_SOURCE_CHARACTERS // (1024 * 1024)} MiB parse limit")
    if not source:
        return ParsedJournal(source="", blocks=(), diagnostics=())

    starts = _line_starts(source)
    blocks: list[JournalBlock] = []
    diagnostics: list[JournalDiagnostic] = []
    position = 0

    def line_and_column(offset: int) -> tuple[int, int]:
        row = bisect_right(starts, offset) - 1
        return row + 1, offset - starts[row] + 1

    def add_block(start: int, end: int, kind: str, command: str | None = None, diagnostic: str | None = None) -> None:
        line, column = line_and_column(start)
        status = "structurally-recognized" if command and command in known_command_paths else "unverified"
        block = JournalBlock(kind, start, end, line, column, command, status, diagnostic)
        blocks.append(block)
        if diagnostic:
            if kind == "scheme-expression":
                code = "scheme-unclosed"
            elif kind == "comment":
                code = "scheme-comment-unclosed"
            else:
                code = "tui-unclosed-quote"
            diagnostics.append(JournalDiagnostic(code, diagnostic, line, column))

    while position < len(source):
        end_of_line = _line_end(source, position)
        line = source[position:end_of_line]
        command = _tui_path(line)

        if line.lstrip().startswith("#|"):
            comment_end, incomplete = _block_comment_end(source, position)
            end = _line_end(source, comment_end) if comment_end < len(source) else len(source)
            message = "Scheme block comment is not closed; source was preserved." if incomplete else None
            add_block(position, end, "comment", diagnostic=message)
            position = end
            continue

        if _scheme_start(line):
            expression_end, incomplete, unclosed_quote = _scheme_end(source, position)
            end = _line_end(source, expression_end) if expression_end < len(source) else len(source)
            message = None
            if incomplete:
                message = "Scheme expression is not structurally closed; the remaining source is kept raw."
            elif unclosed_quote:
                message = "Scheme string is not structurally closed; the remaining source is kept raw."
            add_block(position, end, "scheme-expression", diagnostic=message)
            position = end
            continue

        if command:
            start = position
            position = end_of_line
            while position < len(source):
                next_end = _line_end(source, position)
                next_line = source[position:next_end]
                if _tui_path(next_line) or _scheme_start(next_line):
                    break
                position = next_end
            raw = source[start:position]
            message = "Quoted TUI text is not closed; source was preserved." if _unclosed_tui_quote(raw) else None
            add_block(start, position, "tui-command", command, message)
            continue

        start = position
        position = end_of_line
        while position < len(source):
            next_end = _line_end(source, position)
            next_line = source[position:next_end]
            if _tui_path(next_line) or _scheme_start(next_line):
                break
            position = next_end
        raw = source[start:position]
        kind = "comment" if all(not part.strip() or part.lstrip().startswith((";", "#|")) for part in raw.splitlines()) else "raw"
        add_block(start, position, kind)

    if blocks and (blocks[0].start != 0 or blocks[-1].end != len(source)):
        raise AssertionError("parser spans do not cover the source")
    if any(left.end != right.start for left, right in zip(blocks, blocks[1:])):
        raise AssertionError("parser spans contain a gap or overlap")
    return ParsedJournal(source=source, blocks=tuple(blocks), diagnostics=tuple(diagnostics))

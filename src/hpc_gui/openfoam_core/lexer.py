"""Lexical scanner for OpenFOAM dictionaries (W65 BASE-001).

Produces tokens with line/column spans. Comments, ``#include`` directives
and executable directives (``#codeStream``, ``#calc``) are tokenized but
never evaluated. The scanner is intentionally small: it does not resolve
includes, macros or dynamic values.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LexToken:
    kind: str  # WORD, NUMBER, STRING, LBRACE, RBRACE, LPAREN, RPAREN, SEMI, DIRECTIVE, COMMENT
    text: str
    line: int
    column: int


EXEC_DIRECTIVES = ("#codeStream", "#calc", "#eval", "#codestream")


def _is_word_char(ch: str) -> bool:
    return ch.isalnum() or ch in "_-./:+<>|$^~*!?"


def lex(text: str) -> list[LexToken]:
    tokens: list[LexToken] = []
    i = 0
    line = 1
    col = 1
    n = len(text)

    def advance(k: int = 1) -> None:
        nonlocal i, line, col
        for _ in range(k):
            if i < n:
                if text[i] == "\n":
                    line += 1
                    col = 1
                else:
                    col += 1
                i += 1

    while i < n:
        ch = text[i]
        if ch in " \t\r\n":
            advance()
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "/":
            start_line, start_col = line, col
            j = i
            while j < n and text[j] != "\n":
                j += 1
            tokens.append(LexToken("COMMENT", text[i:j], start_line, start_col))
            advance(j - i)
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "*":
            start_line, start_col = line, col
            j = text.find("*/", i + 2)
            end = n if j == -1 else j + 2
            tokens.append(LexToken("COMMENT", text[i:end], start_line, start_col))
            advance(end - i)
            continue
        if ch == "#":
            start_line, start_col = line, col
            j = i
            while j < n and text[j] not in " \t\r\n;{}()":
                j += 1
            tokens.append(LexToken("DIRECTIVE", text[i:j], start_line, start_col))
            advance(j - i)
            continue
        if ch in "{}();":
            kind = {"{": "LBRACE", "}": "RBRACE", "(": "LPAREN", ")": "RPAREN", ";": "SEMI"}[ch]
            tokens.append(LexToken(kind, ch, line, col))
            advance()
            continue
        if ch == '"':
            start_line, start_col = line, col
            j = i + 1
            buf = ['"']
            while j < n:
                if text[j] == "\\" and j + 1 < n:
                    buf.append(text[j : j + 2])
                    j += 2
                    continue
                buf.append(text[j])
                if text[j] == '"':
                    j += 1
                    break
                j += 1
            tokens.append(LexToken("STRING", "".join(buf), start_line, start_col))
            advance(j - i)
            continue
        start_line, start_col = line, col
        j = i
        while j < n and _is_word_char(text[j]):
            j += 1
        if j == i:  # unknown single char; keep as word to stay total
            j = i + 1
        word = text[i:j]
        kind = "NUMBER"
        try:
            float(word)
        except ValueError:
            kind = "WORD"
        tokens.append(LexToken(kind, word, start_line, start_col))
        advance(j - i)
    return tokens


def contains_executable_directive(tokens: list[LexToken]) -> bool:
    lowered = [t.text.lower() for t in tokens if t.kind == "DIRECTIVE"]
    return any(d in ("#codestream", "#calc", "#eval") for d in lowered)

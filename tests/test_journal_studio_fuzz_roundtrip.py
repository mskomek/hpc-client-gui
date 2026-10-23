"""Seeded property and fuzz checks for the journal parser and byte codec.

hypothesis is not installed in this environment, so the generators below are
driven by fixed seeds: every run exercises the same inputs and a failure can be
reproduced by its seed number.
"""

from __future__ import annotations

import random

import pytest

from hpc_gui.journal_studio import JournalDocument, decode_journal, parse_journal
from hpc_gui.journal_studio.models import JournalBlock


BOMS = (b"\xef\xbb\xbf", b"\xfe\xff", b"\xff\xfe", b"\x00\x00\xfe\xff", b"\xff\xfe\x00\x00")

ATOMS = (
    "/solve/iterate 10",
    '/file/read-case "a b.cas"',
    "/solve/initialize/hyb-initialization",
    "(define x (+ 1 2))",
    '(define s "a;b\\"c")',
    "; comment",
    ";",
    "#| block |#",
    "#| open",
    "|# stray",
    "#| nested #| inner |# still |#",
    "unknown words here",
    "  /indented/path 3",
    "(",
    ")",
    '"unclosed quote',
    '/quote "x',
    '(display "multi',
    'line")',
    "   ",
    "",
    "é ünïcode ☃",
    "tab\there",
    "\\",
    "\x0c form feed",
)
NOISE = "()\"; #|\\/ \t\r\n\x00abc/"
NEWLINES = ("\n", "\r\n", "\r")


def _random_source(rng: random.Random) -> str:
    parts: list[str] = []
    for _ in range(rng.randint(0, 40)):
        if rng.random() < 0.15:
            parts.append("".join(rng.choice(NOISE) for _ in range(rng.randint(0, 12))))
        else:
            parts.append(rng.choice(ATOMS))
        parts.append(rng.choice(NEWLINES) if rng.random() < 0.3 else "\n")
    return "".join(parts)


def _assert_spans(source: str, blocks: tuple[JournalBlock, ...]) -> None:
    assert "".join(source[block.start : block.end] for block in blocks) == source
    cursor = 0
    for block in blocks:
        assert block.start == cursor and block.end > block.start
        assert block.kind in {"tui-command", "scheme-expression", "comment", "raw"}
        assert block.line == source.count("\n", 0, block.start) + 1
        cursor = block.end
    assert cursor == len(source)


@pytest.mark.parametrize("seed", range(400))
def test_parser_spans_are_exact_and_identity_reorder_is_byte_identical(seed):
    source = _random_source(random.Random(seed))
    parsed = parse_journal(source)

    _assert_spans(source, parsed.blocks)
    assert parsed.reorder(tuple(range(len(parsed.blocks)))) == source
    assert parsed.replace(0, 0, "") == source
    assert parse_journal(source) == parsed


@pytest.mark.parametrize("seed", range(150))
def test_random_text_round_trips_with_and_without_bom_and_newlines(seed):
    rng = random.Random(1000 + seed)
    text = _random_source(rng)
    bom, encoding = rng.choice(
        ((b"", "utf-8"), (b"\xef\xbb\xbf", "utf-8"), (b"\xfe\xff", "utf-16-be"), (b"\xff\xfe", "utf-16-le"))
    )
    data = bom + text.encode(encoding)

    document = JournalDocument.from_bytes(data, path=f"seed-{seed}.jou")
    assert document.text == data[len(bom):].decode(document.encoding)
    assert document.to_bytes() == data
    assert not document.modified

    document.text = document.text + "/solve/iterate 1\n"
    edited = document.to_bytes()
    reloaded = JournalDocument.from_bytes(edited)
    assert reloaded.text == document.text
    assert edited.startswith(document.bom)


@pytest.mark.parametrize("seed", range(200))
def test_arbitrary_bytes_decode_or_fail_with_value_error_only(seed):
    rng = random.Random(5000 + seed)
    data = bytes(rng.randrange(256) for _ in range(rng.randint(0, 300)))
    if data.startswith(BOMS):
        try:
            decoded = decode_journal(data)
        except ValueError:
            return
    else:
        decoded = decode_journal(data)
    assert decoded.encode(decoded.text) == data
    assert JournalDocument.from_bytes(data).to_bytes() == data


def test_bom_crlf_fixture_survives_no_op_round_trip_byte_for_byte():
    original = b"\xef\xbb\xbf; title\r\n/file/set-tui-version \"25.2\"\r\n(define x \"a\\\"b\")\r\n"
    document = JournalDocument.from_bytes(original, path="case.jou")

    assert document.newline == "\r\n"
    assert document.to_bytes() == original
    assert parse_journal(document.text).reorder(tuple(range(len(parse_journal(document.text).blocks)))) == document.text


@pytest.mark.parametrize("payload", [b"\x81", b"/solve/iterate 1\r\n\x8d\r\n", b"\x90\x9d"])
def test_cp1252_undefined_bytes_are_preserved_not_crashed(payload):
    decoded = decode_journal(payload)

    assert decoded.decode_warning is not None
    assert decoded.encode(decoded.text) == payload

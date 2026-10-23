"""Focused regressions for lossless journal parsing and local writes."""

from __future__ import annotations

import hashlib

import pytest

from hpc_gui.journal_studio import JournalDocument, decode_journal, parse_journal
from hpc_gui.journal_studio.document import JournalConflictError, write_local_atomic


def test_no_edit_round_trip_preserves_utf8_bom_and_crlf_bytes():
    original = b'\xef\xbb\xbf; title\r\n/file/set-tui-version "25.2"\r\n; kept\r\n(define x "a\\\"b")\r\n'
    document = JournalDocument.from_bytes(original, path="case.jou")
    parsed = parse_journal(document.text)

    assert parsed.source == document.text
    assert document.to_bytes() == original
    assert document.expected_sha256 == hashlib.sha256(original).hexdigest()


def test_parser_spans_cover_mixed_source_and_keep_unknown_code():
    source = '; comment\n/file/read-case "a.cas"\ny\n\n(define (f x)\n  (+ x 1))\nunknown expression\n'
    parsed = parse_journal(source)

    assert "".join(parsed.text_for(block) for block in parsed.blocks) == source
    assert [block.kind for block in parsed.blocks] == ["comment", "tui-command", "scheme-expression", "raw"]
    assert parsed.blocks[1].command_path == "/file/read-case"
    assert parsed.text_for(parsed.blocks[-1]) == "unknown expression\n"


def test_catalog_match_is_structural_only_and_does_not_claim_runtime_validity():
    parsed = parse_journal("/solve/iterate 500\n", known_command_paths=frozenset({"/solve/iterate"}))

    assert parsed.blocks[0].verification_status == "structurally-recognized"
    assert parsed.blocks[0].kind == "tui-command"


def test_incomplete_scheme_and_quote_are_diagnosed_without_rewrite():
    source = '(define value "open\n; tail kept\n'
    parsed = parse_journal(source)

    assert parsed.diagnostics
    assert parsed.diagnostics[0].code == "scheme-unclosed"
    assert parsed.source == source


def test_span_edit_changes_only_the_requested_text():
    source = '; untouched\n/solve/iterate 500\n(define x 1)\n'
    parsed = parse_journal(source)
    command = next(block for block in parsed.blocks if block.kind == "tui-command")
    replacement = parsed.replace(command.start, command.end, "/solve/iterate 501\n")

    assert replacement == '; untouched\n/solve/iterate 501\n(define x 1)\n'


def test_atomic_save_detects_external_change_and_keeps_external_bytes(tmp_path):
    target = tmp_path / "safe.jou"
    original = b"/solve/iterate 10\n"
    target.write_bytes(original)
    expected = hashlib.sha256(original).hexdigest()
    target.write_bytes(b"external change\n")

    with pytest.raises(JournalConflictError):
        write_local_atomic(target, b"/solve/iterate 11\n", expected_sha256=expected)

    assert target.read_bytes() == b"external change\n"


def test_atomic_save_round_trip_for_new_file(tmp_path):
    target = tmp_path / "new.jou"
    data = decode_journal(b"; new\r\n").encode("; new\r\n")

    digest = write_local_atomic(target, data, expected_sha256=None)

    assert target.read_bytes() == b"; new\r\n"
    assert digest == hashlib.sha256(data).hexdigest()

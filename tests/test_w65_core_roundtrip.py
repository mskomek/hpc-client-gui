"""W65 G01/G40/G43: core lexer/parser/safe-patch/security basics."""
from __future__ import annotations

import pytest

from hpc_gui.openfoam_core import (
    byte_identity_ok, classify_case_path, lex, parse_text,
    scan_case, sha256_bytes, single_token_patch,
)
from hpc_gui.openfoam_core.lexer import contains_executable_directive


def test_lex_spans_and_comments():
    toks = lex("FoamFile\n{\n    version 2.0; // head\n}\n")
    assert toks[0].text == "FoamFile" and toks[0].line == 1 and toks[0].column == 1
    assert any(t.kind == "COMMENT" for t in toks)


def test_parse_valid_and_missing_semi():
    ok = parse_text("FoamFile\n{\n    version 2.0;\n}\napplication simpleFoam;\n")
    assert "application" in ok.entries and not ok.issues
    bad = parse_text("application simpleFoam\n")
    assert any("terminating" in i.message for i in bad.issues)


def test_dynamic_directive_never_evaluated():
    toks = lex("#codeStream\n{\ncode #{ 1+1 #};\n}\n")
    assert contains_executable_directive(toks)
    parsed = parse_text("#codeStream\n{\ncode 1;\n}\n")
    assert parsed.has_executable_directive


def test_noop_sha_identity_and_bom_crlf():
    data = b"\xef\xbb\xbfFoamFile\r\n{\r\n}\r\n"
    assert byte_identity_ok(data, bytes(data))
    assert sha256_bytes(b"abc") != sha256_bytes(b"abd")
    with pytest.raises(ValueError):
        single_token_patch(data, b"missing", b"x")
    dup = b"a a"
    with pytest.raises(ValueError):
        single_token_patch(dup, b"a", b"b")


def test_single_token_patch_minimal():
    data = "internalField uniform (1 0 0);\n".encode()
    out = single_token_patch(data, b"(1 0 0)", b"(2 0 0)")
    assert b"(2 0 0)" in out and out.count(b"internalField") == 1


def test_case_scan_classes():
    scan = scan_case("case", ["system/controlDict", "constant/transportProperties",
                              "0/U", "constant/polyMesh/points", "Allrun"])
    assert scan.has_system and scan.has_constant and scan.has_fields and scan.has_polymesh
    assert classify_case_path("Allrun") == "script-untrusted"
    assert classify_case_path("surf.stl") == "geometry"

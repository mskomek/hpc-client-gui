"""Strict-CSP local GTK bridge protocol; no native wx dependency."""
import json
from urllib.parse import unquote

from hpc_gui.wx_terminal_url_bridge import (
    encode_terminal_fragment,
    parse_terminal_call,
)


def test_allowlisted_terminal_calls_roundtrip_unicode_and_ansi():
    for snippet, name, expected in (
        ('window.hpcWrite && window.hpcWrite("abc\\r\\n\\u001b[31m");', "hpcWrite", "abc\r\n\x1b[31m"),
        ('window.hpcPaste && window.hpcPaste("üñí\\n");', "hpcPaste", "üñí\n"),
        ("window.hpcFit && window.hpcFit();", "hpcFit", None),
        ("window.hpcClear && window.hpcClear();", "hpcClear", None),
        ("window.hpcFindNext && window.hpcFindNext();", "hpcFindNext", None),
        ("window.hpcSetFontSize && window.hpcSetFontSize(16);", "hpcSetFontSize", 16),
    ):
        parsed = parse_terminal_call(snippet)
        assert parsed == (name, expected)
        fragment = encode_terminal_fragment(3, *parsed)
        assert fragment.startswith("#hpc=")
        envelope = json.loads(unquote(fragment.removeprefix("#hpc=")))
        assert envelope == {"seq": 3, "op": name, "arg": expected}


def test_reject_arbitrary_scripts_and_nonjson_arguments():
    for script in (
        "1 + 1", "eval('x')", "window.location='https://example.com'",
        "window.hpcWrite && window.hpcWrite(alert('oops'));",
        "window.hpcWrite && window.hpcClear();",
        "window.hpcClear && window.hpcClear('unexpected');",
        "window.hpcSetFontSize && window.hpcSetFontSize(-1);",
        "window.hpcSetFontSize && window.hpcSetFontSize(1000);",
        "window.hpcWrite && window.hpcWrite(42);",
    ):
        assert parse_terminal_call(script) is None


def test_strict_page_csp_and_no_remote_ipc():
    from pathlib import Path
    from hpc_gui.wx_terminal_webview import _wx_index_path

    html = Path(_wx_index_path()).read_text(encoding="utf-8")
    assert "script-src 'self'" in html
    assert "'unsafe-eval'" not in html
    assert "connect-src 'none'" in html
    fragment = encode_terminal_fragment(1, "hpcWrite", "https://example.com/key=a&b")
    assert not fragment.startswith("http:")
    assert not fragment.startswith("https:")
    assert "https%3A" in fragment


def test_reject_untrusted_action_envelope():
    import pytest

    with pytest.raises(ValueError):
        encode_terminal_fragment(0, "hpcWrite", "x")
    with pytest.raises(ValueError):
        encode_terminal_fragment(1, "__proto__", None)
    with pytest.raises(ValueError):
        encode_terminal_fragment(True, "hpcWrite", "x")

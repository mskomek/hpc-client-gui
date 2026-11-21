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
        ('window.hpcSetAccessibilityLabel && window.hpcSetAccessibilityLabel("Uçbirim");', "hpcSetAccessibilityLabel", "Uçbirim"),
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
        "window.hpcSetAccessibilityLabel && window.hpcSetAccessibilityLabel(42);",
        "window.hpcSetAccessibilityLabel && window.hpcSetAccessibilityLabel(\"x\" + alert(1));",
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


def test_webkit_fragment_handler_acknowledges_duplicate_without_replaying_data():
    from pathlib import Path

    bridge = Path(__file__).parents[1] / "src/hpc_gui/assets/terminal/wx_bridge.js"
    source = bridge.read_text(encoding="utf-8")
    duplicate = source.index("if (msg.seq <= lastNativeSequence)")
    apply = source.index("window.name = `hpc-terminal:${msg.channel}:${msg.seq}`")
    assert duplicate < apply
    assert "ack();\n      return;" in source[duplicate:apply]
    assert "window.history.replaceState" in source
    assert "msg.arg" not in source[source.index("const stored =") : apply]
    assert "console.log" not in source and "console.debug" not in source


def test_terminal_fragment_channel_is_metadata_only_and_validated():
    channel = "a" * 32
    fragment = encode_terminal_fragment(4, "hpcWrite", "terminal text", channel=channel)
    envelope = json.loads(unquote(fragment.removeprefix("#hpc=")))
    assert envelope == {
        "seq": 4, "op": "hpcWrite", "arg": "terminal text", "channel": channel,
    }

    import pytest

    with pytest.raises(ValueError):
        encode_terminal_fragment(4, "hpcWrite", "x", channel="terminal text")


def test_reject_untrusted_action_envelope():
    import pytest

    with pytest.raises(ValueError):
        encode_terminal_fragment(0, "hpcWrite", "x")
    with pytest.raises(ValueError):
        encode_terminal_fragment(1, "__proto__", None)
    with pytest.raises(ValueError):
        encode_terminal_fragment(True, "hpcWrite", "x")


def test_accessible_label_uses_csp_safe_bridge_not_webkit_eval():
    from hpc_gui.wx_terminal_webview_bridge import TerminalBridgeMixin

    class FakeWebView:
        def __init__(self):
            self.names = []

        def SetName(self, name):
            self.names.append(name)

        def SetAccessibleName(self, name):
            self.names.append(name)

        def RunScript(self, _code):
            raise AssertionError("WebKitGTK must not use RunScript under strict CSP")

    class Panel(TerminalBridgeMixin):
        _closed = False
        _page_loaded = True

        def __init__(self):
            self._webview = FakeWebView()
            self.calls = []

        def _run_js(self, code):
            self.calls.append(code)

    panel = Panel()
    panel._update_accessibility_label()

    assert panel._webview.names
    assert len(panel.calls) == 1
    parsed = parse_terminal_call(panel.calls[0])
    assert parsed is not None and parsed[0] == "hpcSetAccessibilityLabel"
    assert parsed[1] == panel._webview.names[0]


def test_accessible_label_is_bounded_and_rejects_non_string_payloads():
    import pytest

    too_long = "X" * 257
    assert parse_terminal_call(
        "window.hpcSetAccessibilityLabel && "
        f"window.hpcSetAccessibilityLabel({json.dumps(too_long)});"
    ) is None
    assert parse_terminal_call(
        "window.hpcSetAccessibilityLabel && window.hpcSetAccessibilityLabel(null);"
    ) is None
    for value in (too_long, None, 7):
        with pytest.raises(ValueError):
            encode_terminal_fragment(1, "hpcSetAccessibilityLabel", value)

def test_accessible_label_limit_matches_javascript_utf16_units():
    """A Python-short emoji string can still exceed JS's 256-unit limit."""
    import pytest

    accepted = "🙂" * 128  # 256 JavaScript UTF-16 code units
    rejected = "🙂" * 129  # 258 UTF-16 units, but only 129 Python characters
    for value in (accepted, "Uçbirim"):
        script = (
            "window.hpcSetAccessibilityLabel && "
            f"window.hpcSetAccessibilityLabel({json.dumps(value)});"
        )
        assert parse_terminal_call(script) == ("hpcSetAccessibilityLabel", value)
        fragment = encode_terminal_fragment(1, "hpcSetAccessibilityLabel", value)
        payload = json.loads(unquote(fragment.removeprefix("#hpc=")))
        assert payload["arg"] == value

    for value in (rejected, chr(0xD800)):
        script = (
            "window.hpcSetAccessibilityLabel && "
            f"window.hpcSetAccessibilityLabel({json.dumps(value)});"
        )
        assert parse_terminal_call(script) is None
        with pytest.raises(ValueError):
            encode_terminal_fragment(1, "hpcSetAccessibilityLabel", value)

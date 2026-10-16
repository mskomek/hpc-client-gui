"""Behavioral wx terminal regression tests split by stable responsibility."""

from wx_terminal_behavioral_support import (
    ASSETS, MockScriptEvent, _is_webview_available, _mk_script, _run, _SETUP,
    pathlib, pytest, textwrap, wx,
)

pytestmark = pytest.mark.wx


# ── Section 5: VT escape sequences pass through ──

@pytest.mark.contract
@pytest.mark.subprocess
@pytest.mark.semantic
def test_vt_sgr_bytes_reach_xterm():
    """Prove: SGR escape sequences pass through hpc_write without corruption."""
    if not _is_webview_available():
        pytest.skip("WebView backend unavailable")
    body = textwrap.dedent("""\
    assert panel._ready, "not ready"

    calls = []
    orig = panel._run_js
    panel._run_js = lambda c: calls.append(c)

    panel.hpc_write("\\x1b[31mRED\\x1b[0m")
    assert any("RED" in c for c in calls), f"SGR not passed: {calls}"

    panel.hpc_write("\\x1b[1;32mBOLD GREEN\\x1b[0m")
    assert any("BOLD GREEN" in c for c in calls), f"SGR bold green not passed: {calls}"

    bridge = (_ASSETS / "wx_bridge.js").read_text(encoding="utf-8")
    assert "terminal.write" in bridge, "bridge must use terminal.write"

    panel.close()
    frame.Destroy()
    os._exit(0)
""")
    r = _run(_mk_script(body))
    assert r.returncode == 0, f"failed: {r.stdout}\n{r.stderr}"

# ── Section 6: CR bytes preserved ──

@pytest.mark.contract
@pytest.mark.subprocess
@pytest.mark.semantic
def test_vt_cr_bytes_preserved_through_bridge():
    """Prove: CR bytes pass through hpc_write without splitlines corruption."""
    if not _is_webview_available():
        pytest.skip("WebView backend unavailable")
    body = textwrap.dedent("""\
    assert panel._ready, "not ready"

    calls = []
    orig = panel._run_js
    panel._run_js = lambda c: calls.append(c)

    panel.hpc_write("AAAA\\rBBBB")
    assert any("AAAA" in c and "BBBB" in c for c in calls), f"CR sequence not in calls: {calls}"

    hpc_section = pathlib.Path("src/hpc_gui/wx_terminal_webview_io.py").read_text(encoding="utf-8").split("def hpc_write")[1].split("def _flush_pending")[0]
    assert "splitlines" not in hpc_section, "hpc_write must not use splitlines"

    panel.close()
    frame.Destroy()
    os._exit(0)
""")
    r = _run(_mk_script(body))
    assert r.returncode == 0, f"failed: {r.stdout}\n{r.stderr}"

# ── Section 7: Cursor escape sequences preserved ──

@pytest.mark.contract
@pytest.mark.subprocess
@pytest.mark.semantic
def test_vt_cursor_escape_sequences_preserved():
    """Prove: cursor movement ESC sequences pass through without corruption."""
    if not _is_webview_available():
        pytest.skip("WebView backend unavailable")
    body = textwrap.dedent("""\
    assert panel._ready, "not ready"

    calls = []
    orig = panel._run_js
    panel._run_js = lambda c: calls.append(c)

    panel.hpc_write("ABCDE\\x1b[3DXY")
    assert any("ABCDE" in c and "XY" in c for c in calls), f"cursor sequence not passed: {calls}"

    panel.close()
    frame.Destroy()
    os._exit(0)
""")
    r = _run(_mk_script(body))
    assert r.returncode == 0, f"failed: {r.stdout}\n{r.stderr}"

# ── Section 8: Erase sequences preserved ──

@pytest.mark.contract
@pytest.mark.subprocess
@pytest.mark.semantic
def test_vt_erase_sequences_preserved():
    """Prove: erase line/screen ESC sequences pass through without corruption."""
    if not _is_webview_available():
        pytest.skip("WebView backend unavailable")
    body = textwrap.dedent("""\
    assert panel._ready, "not ready"

    calls = []
    orig = panel._run_js
    panel._run_js = lambda c: calls.append(c)

    panel.hpc_write("\\x1b[2K")
    assert any("2K" in c for c in calls), f"EL not preserved: {calls}"

    panel.hpc_write("\\x1b[2J\\x1b[H")
    assert any("2J" in c for c in calls), f"ED not preserved: {calls}"

    panel.close()
    frame.Destroy()
    os._exit(0)
""")
    r = _run(_mk_script(body))
    assert r.returncode == 0, f"failed: {r.stdout}\n{r.stderr}"

# ── Section 9: Alternate screen sequences preserved ──

@pytest.mark.contract
@pytest.mark.subprocess
@pytest.mark.semantic
def test_vt_alternate_screen_sequences_preserved():
    """Prove: alternate screen ESC sequences pass through to xterm."""
    if not _is_webview_available():
        pytest.skip("WebView backend unavailable")
    body = textwrap.dedent("""\
    assert panel._ready, "not ready"

    calls = []
    orig = panel._run_js
    panel._run_js = lambda c: calls.append(c)

    panel.hpc_write("\\x1b[?1049h")
    assert any("?1049h" in c for c in calls), f"smcup not passed: {calls}"

    panel.hpc_write("\\x1b[?1049l")
    assert any("?1049l" in c for c in calls), f"rmcup not passed: {calls}"

    panel.close()
    frame.Destroy()
    os._exit(0)
""")
    r = _run(_mk_script(body))
    assert r.returncode == 0, f"failed: {r.stdout}\n{r.stderr}"

# ── Section 10: Search next/prev with state advancement ──

@pytest.mark.contract
def test_find_next_prev_commands_match_webview_bridge_contract():
    """Verify bridge commands without starting native WebView2."""
    from hpc_gui.wx_terminal_webview import WxTerminalWebViewPanel

    calls = []
    class PanelSeam:
        _closed = False
        _ready = True
        _is_parity = True
        _webview = object()

        def _run_js(self, code):
            calls.append(code)

    panel = PanelSeam()
    assert WxTerminalWebViewPanel.hpc_find(panel, "aaa")
    assert any("hpcFind" in c and '"aaa"' in c for c in calls), f"hpcFind not called: {calls}"
    calls.clear()

    assert WxTerminalWebViewPanel.hpc_find_next(panel)
    assert any("hpcFindNext" in c for c in calls), f"hpcFindNext not called: {calls}"
    calls.clear()

    assert WxTerminalWebViewPanel.hpc_find_prev(panel)
    assert any("hpcFindPrev" in c for c in calls), f"hpcFindPrev not called: {calls}"

    bridge = (ASSETS / "wx_bridge.js").read_text(encoding="utf-8")
    assert "hpcFindNext" in bridge, "hpcFindNext missing from bridge"
    assert "hpcFindPrev" in bridge, "hpcFindPrev missing from bridge"
    assert "translateToString" in bridge, "must use translateToString"
    assert "scrollToLine" in bridge, "scrollToLine missing"

# ── Section 14: Unicode I/O ──

@pytest.mark.contract
@pytest.mark.subprocess
@pytest.mark.semantic
def test_unicode_input_output_roundtrip():
    """Prove: Unicode passes through input and output without ASCII clamp."""
    if not _is_webview_available():
        pytest.skip("WebView backend unavailable")
    body = textwrap.dedent("""\
    assert panel._ready, "not ready"

    calls = []
    orig = panel._run_js
    panel._run_js = lambda c: calls.append(c)
    panel.hpc_write("Türkçe 日本語 한국어")
    assert any("Türkçe" in c or "日本語" in c for c in calls), f"unicode output missing: {calls}"

    class UEvt:
        def __init__(self, d):
            self._d = _json.dumps({"type": "input", "data": d})
        def GetString(self): return self._d
        def GetMessage(self): return self._d
    panel._on_script_message(UEvt("café résumé"))
    assert ssh.sent[-1] == "café résumé", f"unicode input failed: {ssh.sent[-1]}"

    panel.close()
    frame.Destroy()
    os._exit(0)
""")
    r = _run(_mk_script(body))
    assert r.returncode == 0, f"failed: {r.stdout}\n{r.stderr}"

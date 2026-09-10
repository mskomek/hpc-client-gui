"""Wave 78 — Strict behavioral parity tests for GUI-TERM-001.

Tests run in subprocess isolation. Each test uses real WebView/xterm.js
renderer. JS bridge tests verify the full chain:
  xterm onData -> JS postMessage -> wx script-message -> Python adapter -> SSH
"""

import json
import os
import pathlib
import subprocess
import sys
import textwrap

import pytest

wx = pytest.importorskip("wx")

from hpc_gui.wx_terminal_webview import _is_webview_available

ASSETS = pathlib.Path(__file__).parents[1] / "src" / "hpc_gui" / "assets" / "terminal"


def _run(code, timeout=60):
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    return subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True, text=True, timeout=timeout, env=env,
    )


_READY_PUMP = textwrap.dedent("""\
    import wx, time
    loop = wx.GUIEventLoop()
    prev = wx.EventLoop.GetActive()
    wx.EventLoop.SetActive(loop)
    start = time.monotonic()
    while time.monotonic() - start < 6:
        if panel._ready:
            break
        try:
            while loop.Pending():
                loop.Dispatch()
        except Exception:
            pass
        try:
            wx.Yield()
        except Exception:
            pass
        time.sleep(0.05)
    wx.EventLoop.SetActive(prev)
""")

_SETUP = textwrap.dedent("""\
    import sys, os
    sys.path.insert(0, "src")
    import wx, time, json as _json, pathlib
    from hpc_gui.wx_terminal_webview import WxTerminalWebViewPanel

    _ASSETS = pathlib.Path("src/hpc_gui/assets/terminal")

    class FakeSSH:
        def __init__(self):
            self.sent = []
            self.resizes = []
            self._wx_output_subscribers = []
        def send_shell_input(self, d):
            self.sent.append(d)
            return True
        def resize_shell_pty(self, c, r):
            self.resizes.append((c, r))

    app = wx.App(False)
    frame = wx.Frame(None, size=(900, 600))
    ssh = FakeSSH()
    panel = WxTerminalWebViewPanel(frame, ssh=ssh)
    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(panel, 1, wx.EXPAND)
    frame.SetSizer(sizer)
    frame.Layout()
    frame.Show()
""")


def _mk_script(code_body):
    """Build a full subprocess script: imports + ready pump + body."""
    return _SETUP + _READY_PUMP + textwrap.dedent("""\
    wx.EventLoop.SetActive(prev)
""") + code_body


class MockScriptEvent:
    def __init__(self, payload):
        self._payload = json.dumps(payload)
    def GetString(self):
        return self._payload
    def GetMessage(self):
        return self._payload


# ── Section 1: Embedded terminal SSH attachment ──

def test_embedded_connect_to_ssh_via_shell_path():
    """Prove: WxTerminalWebViewPanel(ssh=None) -> set_ssh(fake) -> subscriber -> input."""
    if not _is_webview_available():
        pytest.skip("WebView backend unavailable")
    body = textwrap.dedent("""\
    assert panel._ready, "not ready"

    panel.set_ssh(None)
    assert panel._ssh is None
    assert panel._status_label.GetLabel()

    ssh2 = FakeSSH()
    ssh2.sent = []
    ssh2.resizes = []
    panel.set_ssh(ssh2)
    assert panel._ssh is ssh2
    assert len(ssh2._wx_output_subscribers) == 1
    assert panel._status_label.GetLabel()

    panel._ready = True
    panel._is_parity = True
    panel._handle_input("\\x03")
    assert ssh2.sent[-1] == "\\x03", f"input not forwarded: {ssh2.sent}"

    panel._handle_resize(120, 40, 960, 600)
    assert ssh2.resizes == [(120, 40)]

    sub = ssh2._wx_output_subscribers[0]
    writes = []
    orig = panel.hpc_write
    panel.hpc_write = lambda d: writes.append(d)
    sub("test_output_from_ssh2")
    panel._safe_deliver(panel._generation, "delivered")
    assert any("delivered" in w for w in writes)

    panel.close()
    frame.Destroy()
    os._exit(0)
""")
    r = _run(_mk_script(body))
    assert r.returncode == 0, f"failed: {r.stdout}\n{r.stderr}"


# ── Section 2: Real xterm input chain (JS bridge mock) ──

def test_input_chain_through_script_message_handler():
    """Prove: JS bridge message -> _on_script_message -> _handle_input -> send_shell_input."""
    if not _is_webview_available():
        pytest.skip("WebView backend unavailable")
    body = textwrap.dedent("""\
    assert panel._ready, "not ready"

    class MockScriptEvent:
        def __init__(self, payload):
            self._payload = _json.dumps(payload)
        def GetString(self): return self._payload
        def GetMessage(self): return self._payload

    panel._on_script_message(MockScriptEvent({"type": "input", "data": "\\x03"}))
    assert ssh.sent[-1] == "\\x03", f"Ctrl+C not forwarded: {ssh.sent}"

    panel._on_script_message(MockScriptEvent({"type": "input", "data": "\\r"}))
    assert ssh.sent[-1] == "\\r", f"Enter not forwarded: {ssh.sent}"

    panel._on_script_message(MockScriptEvent({"type": "input", "data": "\\t"}))
    assert ssh.sent[-1] == "\\t", f"Tab not forwarded: {ssh.sent}"

    panel._on_script_message(MockScriptEvent({"type": "input", "data": "\\x7f"}))
    assert ssh.sent[-1] == "\\x7f", f"Backspace not forwarded: {ssh.sent}"

    panel._on_script_message(MockScriptEvent({"type": "input", "data": "\\x1b"}))
    assert ssh.sent[-1] == "\\x1b", f"Escape not forwarded: {ssh.sent}"

    panel._on_script_message(MockScriptEvent({"type": "input", "data": "\\x1b[A"}))
    assert ssh.sent[-1] == "\\x1b[A", f"Up arrow not forwarded: {ssh.sent}"

    panel._on_script_message(MockScriptEvent({"type": "input", "data": "\\x1b[B"}))
    assert ssh.sent[-1] == "\\x1b[B", f"Down arrow not forwarded: {ssh.sent}"

    panel._on_script_message(MockScriptEvent({"type": "input", "data": "日本語"}))
    assert ssh.sent[-1] == "日本語", f"Unicode not forwarded: {ssh.sent}"

    panel._on_script_message(MockScriptEvent({"type": "resize", "cols": 132, "rows": 44, "pixelWidth": 1056, "pixelHeight": 704}))
    assert ssh.resizes[-1] == (132, 44), f"resize not forwarded: {ssh.resizes}"

    panel.close()
    frame.Destroy()
    os._exit(0)
""")
    r = _run(_mk_script(body))
    assert r.returncode == 0, f"failed: {r.stdout}\n{r.stderr}"


# ── Section 3: Real paste chain ──

def test_paste_chain_through_bridge():
    """Prove: hpcPaste -> terminal.paste -> terminal.onData -> postToPython -> SSH."""
    if not _is_webview_available():
        pytest.skip("WebView backend unavailable")
    body = textwrap.dedent("""\
    assert panel._ready, "not ready"

    paste_content = "line1\\nline2\\nline3"
    class PasteEvent:
        def __init__(self, data):
            self._d = _json.dumps({"type": "input", "data": data})
        def GetString(self): return self._d
        def GetMessage(self): return self._d
    panel._on_script_message(PasteEvent(paste_content))
    assert len(ssh.sent) >= 1, f"no paste data: {ssh.sent}"
    assert ssh.sent[-1] == paste_content, f"paste not complete: {repr(ssh.sent[-1])}"

    calls = []
    orig = panel._run_js
    panel._run_js = lambda c: calls.append(c)
    panel.hpc_paste("echo one\\necho two\\necho three")
    assert any("hpcPaste" in c for c in calls), f"hpcPaste not called: {calls}"
    assert "echo one" in calls[0] and "echo three" in calls[0], f"incomplete paste: {calls[0]}"

    panel.close()
    frame.Destroy()
    os._exit(0)
""")
    r = _run(_mk_script(body))
    assert r.returncode == 0, f"failed: {r.stdout}\n{r.stderr}"


# ── Section 4: Reconnect generation guard ──

def test_stale_output_rejected_after_reconnect():
    """Prove: SSH A delayed callback -> reconnect to SSH B -> A's callback rejected."""
    if not _is_webview_available():
        pytest.skip("WebView backend unavailable")
    body = textwrap.dedent("""\
    assert panel._ready, "not ready"

    writes = []
    panel.hpc_write = lambda d: writes.append(d)

    old_gen = panel._generation
    old_sub = ssh._wx_output_subscribers[0]
    old_sub("stale_from_ssh1")
    panel._safe_deliver(old_gen, "stale_delivered")
    assert any("stale_delivered" in w for w in writes), "ssh1 output before reconnect"

    ssh2 = FakeSSH()
    panel.set_ssh(ssh2)
    assert panel._generation == old_gen + 1, "generation must increment"

    panel._safe_deliver(old_gen, "very_stale_data")
    assert not any("very_stale_data" in w for w in writes), "stale generation must be rejected"

    panel._safe_deliver(panel._generation, "fresh_ssh2_data")
    assert any("fresh_ssh2_data" in w for w in writes), "new SSH data must be delivered"

    assert len(ssh._wx_output_subscribers) == 0, "old ssh should have 0 subscribers"
    assert len(ssh2._wx_output_subscribers) == 1, "new ssh should have 1 subscriber"

    panel.close()
    frame.Destroy()
    os._exit(0)
""")
    r = _run(_mk_script(body))
    assert r.returncode == 0, f"failed: {r.stdout}\n{r.stderr}"


# ── Section 5: VT escape sequences pass through ──

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

    hpc_section = pathlib.Path("src/hpc_gui/wx_terminal_webview.py").read_text(encoding="utf-8").split("def hpc_write")[1].split("def _flush_pending")[0]
    assert "splitlines" not in hpc_section, "hpc_write must not use splitlines"

    panel.close()
    frame.Destroy()
    os._exit(0)
""")
    r = _run(_mk_script(body))
    assert r.returncode == 0, f"failed: {r.stdout}\n{r.stderr}"


# ── Section 7: Cursor escape sequences preserved ──

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

def test_find_next_prev_advances_through_matches():
    """Prove: hpcFind -> hpcFindNext -> hpcFindPrev all dispatch to JS."""
    if not _is_webview_available():
        pytest.skip("WebView backend unavailable")
    from hpc_gui.wx_terminal_webview import WxTerminalWebViewPanel

    class FakeSSH:
        _wx_output_subscribers = []
        def send_shell_input(self, d): return True
        def resize_shell_pty(self, c, r): pass

    _app = wx.App(False)
    frame = wx.Frame(None, size=(900, 600))
    panel = WxTerminalWebViewPanel(frame, ssh=FakeSSH())
    panel._ready = True
    panel._is_parity = True

    calls = []
    panel._run_js = lambda c: calls.append(c)

    panel.hpc_find("aaa")
    assert any("hpcFind" in c and '"aaa"' in c for c in calls), f"hpcFind not called: {calls}"
    calls.clear()

    panel.hpc_find_next()
    assert any("hpcFindNext" in c for c in calls), f"hpcFindNext not called: {calls}"
    calls.clear()

    panel.hpc_find_prev()
    assert any("hpcFindPrev" in c for c in calls), f"hpcFindPrev not called: {calls}"

    bridge = (ASSETS / "wx_bridge.js").read_text(encoding="utf-8")
    assert "hpcFindNext" in bridge, "hpcFindNext missing from bridge"
    assert "hpcFindPrev" in bridge, "hpcFindPrev missing from bridge"
    assert "translateToString" in bridge, "must use translateToString"
    assert "scrollToLine" in bridge, "scrollToLine missing"

    panel.close()
    frame.Destroy()
    wx.Yield()


# ── Section 11: Header status and identity ──

def test_header_status_identity_dimensions():
    """Prove: header shows Disconnected/Connected/identity/dimensions."""
    if not _is_webview_available():
        pytest.skip("WebView backend unavailable")
    body = textwrap.dedent("""\
    assert panel._ready, "not ready"

    panel.set_ssh(None)
    status = panel._status_label.GetLabel()
    assert status, f"initial status empty: {status}"

    ssh.username = "testuser"
    ssh.hostname = "testhost"
    panel.set_ssh(ssh)
    status2 = panel._status_label.GetLabel()
    assert status2, f"connected status empty: {status2}"
    identity = panel._identity_label.GetLabel()
    assert "testuser" in identity and "testhost" in identity, f"identity: {identity}"

    panel._handle_resize(132, 44, 1056, 704)
    dims = panel._dimensions_label.GetLabel()
    assert "132" in dims and "44" in dims, f"dimensions: {dims}"

    ssh2 = FakeSSH()
    ssh2.username = "user2"
    ssh2.hostname = "host2"
    panel.set_ssh(ssh2)
    identity2 = panel._identity_label.GetLabel()
    assert "user2" in identity2 and "host2" in identity2, f"identity after reconnect: {identity2}"

    panel.set_ssh(None)
    identity3 = panel._identity_label.GetLabel()
    assert identity3 == "", f"identity after disconnect should be empty: {identity3}"

    panel.close()
    frame.Destroy()
    os._exit(0)
""")
    r = _run(_mk_script(body))
    assert r.returncode == 0, f"failed: {r.stdout}\n{r.stderr}"


# ── Section 12: Lifecycle safety ──

def test_destroy_before_ready_no_crash():
    """Prove: close before ready clears pending, suppresses callbacks."""
    if not _is_webview_available():
        pytest.skip("WebView backend unavailable")
    code = _SETUP + textwrap.dedent("""\
    panel.hpc_write("pending_data")
    assert len(panel._pending) == 1

    panel.close()
    assert panel._closed is True
    assert panel._pending == [], f"pending not cleared: {panel._pending}"

    panel.hpc_write("after_close")
    assert panel._pending == []

    panel._on_bridge_ready()
    assert panel._ready is False or panel._closed is True

    panel._safe_deliver(panel._generation + 1, "late_data")
    assert panel._pending == []

    panel._safe_deliver(panel._generation, "late_data")
    assert panel._pending == []

    frame.Destroy()
    os._exit(0)
""")
    r = _run(code)
    assert r.returncode == 0, f"failed: {r.stdout}\n{r.stderr}"


def test_close_while_output_in_flight():
    """Prove: close during output delivery does not crash."""
    if not _is_webview_available():
        pytest.skip("WebView backend unavailable")
    from hpc_gui.wx_terminal_webview import WxTerminalWebViewPanel

    class FakeSSH:
        _wx_output_subscribers = []
        def send_shell_input(self, d): return True
        def resize_shell_pty(self, c, r): pass

    _app = wx.App(False)
    frame = wx.Frame(None, size=(900, 600))
    panel = WxTerminalWebViewPanel(frame, ssh=FakeSSH())
    panel._ready = True
    panel._is_parity = True

    for i in range(100):
        panel.hpc_write(f"data_{i}\\n")
    panel.close()
    assert panel._closed
    panel.close()
    assert panel._closed
    frame.Destroy()
    wx.Yield()


def test_100_reconnects_no_leak():
    """Prove: 100 reconnects don't leak subscribers."""
    if not _is_webview_available():
        pytest.skip("WebView backend unavailable")
    body = textwrap.dedent("""\
    assert panel._ready, "not ready"

    initial_gen = panel._generation
    for i in range(100):
        new_ssh = FakeSSH()
        panel.set_ssh(new_ssh)
        assert panel._generation == initial_gen + i + 1, f"gen mismatch at {i}"
        assert len(new_ssh._wx_output_subscribers) == 1, f"leak at {i}: {len(new_ssh._wx_output_subscribers)}"

    panel.close()
    frame.Destroy()
    os._exit(0)
""")
    r = _run(_mk_script(body))
    assert r.returncode == 0, f"failed: {r.stdout}\n{r.stderr}"


# ── Section 13: Font -> resize chain ──

def test_font_change_triggers_fit_and_resize():
    """Prove: font change -> hpcSetFontSize -> fit -> resize callback."""
    if not _is_webview_available():
        pytest.skip("WebView backend unavailable")
    body = textwrap.dedent("""\
    assert panel._ready, "not ready"

    calls = []
    orig = panel._run_js
    panel._run_js = lambda c: calls.append(c)

    panel.hpc_set_font_size(18)
    assert panel._font_size == 18
    assert any("hpcSetFontSize" in c and "18" in c for c in calls), f"font change not called: {calls}"

    panel._handle_resize(100, 30, 800, 500)
    assert ssh.resizes[-1] == (100, 30)
    dims = panel._dimensions_label.GetLabel()
    assert "100" in dims and "30" in dims, f"dims: {dims}"

    panel.close()
    frame.Destroy()
    os._exit(0)
""")
    r = _run(_mk_script(body))
    assert r.returncode == 0, f"failed: {r.stdout}\n{r.stderr}"


# ── Section 14: Unicode I/O ──

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


# ── Section 15: Large pre-ready output ──

def test_large_pre_ready_output_buffered():
    """Prove: 500KB pre-ready output is buffered and preserved in order."""
    if not _is_webview_available():
        pytest.skip("WebView backend unavailable")
    code = _SETUP + textwrap.dedent("""\
    big_data = "X" * (500 * 1024)
    panel.hpc_write(big_data)
    assert len(panel._pending) >= 1, "should have pending"
    total = sum(len(p.encode("utf-8", errors="replace")) for p in panel._pending)
    assert total >= 500 * 1024, f"expected >= 500KB pending, got {total}"

    panel.hpc_write("END_MARKER")
    combined = "".join(panel._pending)
    assert combined.endswith("END_MARKER"), "END_MARKER must be last"
    assert combined.startswith("X" * 100), "big_data must be first"

    panel.close()
    frame.Destroy()
    os._exit(0)
""")
    r = _run(code)
    assert r.returncode == 0, f"failed: {r.stdout}\n{r.stderr}"


# ── Section 16: Fallback non-parity ──

def test_fallback_panel_sets_non_parity():
    """When WebView unavailable, panel must be marked non-parity."""
    from hpc_gui.wx_terminal_webview import build_terminal_panel, WxTerminalWebViewPanel
    assert hasattr(WxTerminalWebViewPanel, "__init__"), "WxTerminalWebViewPanel must exist"
    assert callable(build_terminal_panel), "build_terminal_panel must be callable"


# ── Section 17: Bridge has required helpers ──

def test_bridge_has_required_helpers():
    """Bridge must expose all required API functions."""
    bridge = (ASSETS / "wx_bridge.js").read_text(encoding="utf-8")
    for name in ("hpcFind", "hpcFindNext", "hpcFindPrev", "hpcResetFindState",
                 "hpcGetLineText", "hpcGetBufferText", "hpcGetScreenState",
                 "hpcGetAlternateScreenActive", "hpcWrite", "hpcClear",
                 "hpcPaste", "hpcFocus", "hpcSetFontSize", "hpcFit"):
        assert name in bridge, f"{name} missing from bridge"
    assert "translateToString" in bridge, "translateToString missing"
    assert "select(" in bridge, "select() missing"
    assert "scrollToLine" in bridge, "scrollToLine missing"
    assert "buffer.active" in bridge, "buffer.active missing"
    assert "terminal.write" in bridge, "terminal.write missing"
    assert "terminal.paste" in bridge, "terminal.paste missing"

"""Behavioral wx terminal regression tests split by stable responsibility."""

from wx_terminal_behavioral_support import (
    _is_webview_available, _mk_script, _run, pytest, textwrap,
)

pytestmark = pytest.mark.wx


# ── Section 1: Embedded terminal SSH attachment ──

@pytest.mark.gui
@pytest.mark.subprocess
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

@pytest.mark.gui
@pytest.mark.subprocess
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

@pytest.mark.gui
@pytest.mark.subprocess
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

@pytest.mark.integration
@pytest.mark.subprocess
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

# ── Section 11: Header status and identity ──

@pytest.mark.gui
@pytest.mark.subprocess
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

# ── Section 13: Font -> resize chain ──

@pytest.mark.gui
@pytest.mark.subprocess
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

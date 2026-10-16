"""Behavioral wx terminal regression tests split by stable responsibility."""

from wx_terminal_behavioral_support import (
    ASSETS, MockScriptEvent, _is_webview_available, _mk_script, _run, _SETUP,
    pathlib, pytest, textwrap, wx,
)

pytestmark = pytest.mark.wx


# ── Section 12: Lifecycle safety ──

@pytest.mark.unit
@pytest.mark.subprocess
@pytest.mark.resource
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


@pytest.mark.unit
def test_close_while_output_in_flight():
    """Prove: close during output delivery does not crash."""
    if not _is_webview_available():
        pytest.skip("WebView backend unavailable")
    from hpc_gui.wx_terminal_webview import WxTerminalWebViewPanel

    class FakeSSH:
        _wx_output_subscribers = []
        def send_shell_input(self, d): return True
        def resize_shell_pty(self, c, r): pass

    _app = wx.App.Get()
    if _app is None:
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


@pytest.mark.unit
@pytest.mark.subprocess
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

# ── Section 15: Large pre-ready output ──

@pytest.mark.unit
@pytest.mark.subprocess
@pytest.mark.semantic
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

@pytest.mark.gui
@pytest.mark.subprocess
def test_fallback_panel_sets_non_parity():
    """The public terminal builder falls back to a working text terminal."""
    code = """
import os, sys
sys.path.insert(0, "src")
import wx
import hpc_gui.wx_terminal_webview as renderer
renderer._is_webview_available = lambda: False
from hpc_gui.wx_terminal import build_terminal_panel
app = wx.App.Get()
if app is None:
    app = wx.App(False)
frame = wx.Frame(None, size=(600, 400))
panel = build_terminal_panel(frame)
frame.Show()
wx.Yield()
controls = panel._wx_terminal_controls
assert controls["output"].IsShown()
panel._wx_terminal_render("fallback-output-marker")
assert controls["output"].GetValue() == "fallback-output-marker"
clear = controls["clear"]
clear.GetEventHandler().ProcessEvent(wx.CommandEvent(wx.wxEVT_BUTTON, clear.GetId()))
assert controls["output"].GetValue() == ""
panel._wx_terminal_close()
frame.Destroy()
os._exit(0)
"""
    result = _run(code)
    assert result.returncode == 0, f"fallback behavior failed: {result.stdout}\n{result.stderr}"

# ── Section 17: Bridge has required helpers ──

@pytest.mark.contract
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

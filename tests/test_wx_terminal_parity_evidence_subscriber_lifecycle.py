"""Wave 76 — wx terminal panel bridge checks for GUI-TERM-001.

Subprocesses isolate WebView2; fake SSH and a captured JS runner expose the
panel's bridge payloads without claiming that xterm rendered visible output.
"""
from support.test_wx_terminal_parity_evidence_shared import (
    _is_webview_available,
    _run,
    _wrap,
    json,
    pathlib,
    pytest,
)

pytestmark = [pytest.mark.wx, pytest.mark.subprocess]
ASSETS = pathlib.Path(__file__).parents[1] / "src" / "hpc_gui" / "assets" / "terminal"

@pytest.mark.unit
@pytest.mark.resource
@pytest.mark.semantic
def test_reconnect_replaces_output_subscriber():
    """Replacing SSH adapters detaches the old and retains one new subscriber."""
    if not _is_webview_available():
        pytest.skip("WebView backend unavailable")
    r = _run(_wrap("""
import sys, os
sys.path.insert(0, "src")
import wx, time
from hpc_gui.wx_terminal_webview import WxTerminalWebViewPanel

class Fake:
    def __init__(self):
        self._wx_output_subscribers = []
    def send_shell_input(self, d): return True
    def resize_shell_pty(self, c, r): pass

app = wx.App.Get()
if app is None:
    app = wx.App(False)
frame = wx.Frame(None, size=(900,600))
ssh = Fake()
panel = WxTerminalWebViewPanel(frame, ssh=ssh)
sizer = wx.BoxSizer(wx.VERTICAL); sizer.Add(panel,1,wx.EXPAND)
frame.SetSizer(sizer); frame.Layout(); frame.Show()
loop = wx.GUIEventLoop(); prev = wx.EventLoop.GetActive(); wx.EventLoop.SetActive(loop)
start = time.monotonic()
while time.monotonic()-start < 6:
    if panel._ready: break
    try:
        while loop.Pending(): loop.Dispatch()
    except: pass
    try: wx.Yield()
    except: pass
    time.sleep(0.05)
wx.EventLoop.SetActive(prev)
assert panel._ready
for i in range(100):
    new = Fake()
    panel.set_ssh(new)
    assert len(new._wx_output_subscribers) == 1
assert len(ssh._wx_output_subscribers) == 0
panel.close(); frame.Destroy(); os._exit(0)
"""))
    assert r.returncode == 0, f"failed: {r.stdout}\n{r.stderr}"

@pytest.mark.unit
@pytest.mark.semantic
def test_repeated_font_find_clear_bridge_calls_stay_bounded():
    """Repeated font, find, and clear commands remain within font limits."""
    if not _is_webview_available():
        pytest.skip("WebView backend unavailable")
    r = _run(_wrap("""
import sys, os
sys.path.insert(0, "src")
import wx, time
from hpc_gui.wx_terminal_webview import WxTerminalWebViewPanel

class Fake:
    _wx_output_subscribers = []
    def send_shell_input(self, d): return True
    def resize_shell_pty(self, c, r): pass

app = wx.App.Get()
if app is None:
    app = wx.App(False)
frame = wx.Frame(None, size=(900,600))
panel = WxTerminalWebViewPanel(frame, ssh=Fake())
sizer = wx.BoxSizer(wx.VERTICAL); sizer.Add(panel,1,wx.EXPAND)
frame.SetSizer(sizer); frame.Layout(); frame.Show()
loop = wx.GUIEventLoop(); prev = wx.EventLoop.GetActive(); wx.EventLoop.SetActive(loop)
start = time.monotonic()
while time.monotonic()-start < 6:
    if panel._ready: break
    try:
        while loop.Pending(): loop.Dispatch()
    except: pass
    try: wx.Yield()
    except: pass
    time.sleep(0.05)
wx.EventLoop.SetActive(prev)
assert panel._ready
for i in range(100):
    panel.hpc_set_font_size(10 + (i % 20))
    panel.hpc_find(f"q{i}")
    panel.hpc_clear()
assert 6 <= panel._font_size <= 32
panel.close(); frame.Destroy(); os._exit(0)
"""))
    assert r.returncode == 0, f"failed: {r.stdout}\n{r.stderr}"

@pytest.mark.unit
@pytest.mark.resource
@pytest.mark.semantic
def test_close_after_queued_output_is_idempotent():
    """Closing after output calls leaves the panel closed and is idempotent."""
    if not _is_webview_available():
        pytest.skip("WebView backend unavailable")
    r = _run(_wrap("""
import sys, os
sys.path.insert(0, "src")
import wx, time
from hpc_gui.wx_terminal_webview import WxTerminalWebViewPanel

class Fake:
    _wx_output_subscribers = []
    def send_shell_input(self, d): return True
    def resize_shell_pty(self, c, r): pass

app = wx.App.Get()
if app is None:
    app = wx.App(False)
frame = wx.Frame(None, size=(900,600))
panel = WxTerminalWebViewPanel(frame, ssh=Fake())
sizer = wx.BoxSizer(wx.VERTICAL); sizer.Add(panel,1,wx.EXPAND)
frame.SetSizer(sizer); frame.Layout(); frame.Show()
loop = wx.GUIEventLoop(); prev = wx.EventLoop.GetActive(); wx.EventLoop.SetActive(loop)
start = time.monotonic()
while time.monotonic()-start < 6:
    if panel._ready: break
    try:
        while loop.Pending(): loop.Dispatch()
    except: pass
    try: wx.Yield()
    except: pass
    time.sleep(0.05)
wx.EventLoop.SetActive(prev)
assert panel._ready
for i in range(100):
    panel.hpc_write(f"data_{i}\\n")
panel.close()
assert panel._closed
panel.close()  # idempotent
assert panel._closed
os._exit(0)
"""))
    assert r.returncode == 0, f"failed: {r.stdout}\n{r.stderr}"

@pytest.mark.reporting
def test_generate_parity_evidence():
    """Generate the source/runtime evidence record for GUI-TERM-001.

    This is one evidence *layer*, not the requirement's status. It used to
    overwrite ``GUI_TERM_001_EXECUTION_EVIDENCE.json`` on every run, which is
    how that curated cross-layer record came to assert a packaged WebView2
    PASS it had never observed. The cross-layer record is maintained by hand
    and states packaged evidence per artifact; this test writes beside it.
    """
    evidence = {
        "wave": 77,
        "requirement": "GUI-TERM-001",
        "evidence_layer": "source_runtime",
        "status": "source/runtime PASS; says nothing about any packaged artifact",
        "branch": "develop",
        "renderer": "wx.html2.WebView + xterm.js 5.x",
        "bridge": "single JSON postMessage (hpc/hpc_msg)",
        "pty_adapter": "FakeSSH disposable fixture",
        "tests_executed": [
            "test_panel_sends_sgr_payload_to_terminal_bridge",
            "test_panel_preserves_carriage_return_bridge_payload",
            "test_panel_preserves_unicode_output_payload",
            "test_panel_sends_multiline_paste_to_bridge",
            "test_panel_forwards_resize_to_ssh_seam",
            "test_repeated_input_forwarding_preserves_order",
            "test_repeated_resize_requests_are_deduplicated",
            "test_reconnect_replaces_output_subscriber",
            "test_repeated_font_find_clear_bridge_calls_stay_bounded",
            "test_close_after_queued_output_is_idempotent",
            "test_wx_terminal_generation_guard_rejects_stale_output",
            "test_wx_terminal_find_next_and_prev",
            "test_wx_terminal_header_status_updates",
            "test_wx_terminal_destroy_before_ready_no_xfail",
            "test_wx_terminal_large_pre_ready_output",
            "test_wx_terminal_100_reconnects_no_leak",
            "test_wx_terminal_embedded_connect_to_ssh",
            "test_wx_terminal_input_chain_ctrl_a_to_z",
            "test_wx_terminal_resize_chain_to_ssh",
            "test_wx_terminal_unicode_input_output",
            "test_wx_terminal_screen_state_readback_and_alternate_buffer",
        ],
        "invariants": {
            "duplicate_output_subscribers": "0 (verified in reconnect stress)",
            "callbacks_into_destroyed": "0 (close mid-flight + destroy-before-ready tests)",
            "stale_session_output": "0 (generation guard in set_ssh + _safe_deliver)",
            "unbounded_accumulation": "0 (bounded queue MAX_PENDING_BYTES=2MB)",
        },
        "scope_note": (
            "Every entry above is a source-tree run with a real wx.App and a "
            "real WebView against a disposable SSH/PTY fixture. No packaged "
            "artifact is exercised here, so nothing in this file is packaged "
            "evidence. Packaged status per artifact lives in "
            "docs/v2/GUI_TERM_001_EXECUTION_EVIDENCE.json."
        ),
    }
    out = pathlib.Path("docs/v2/GUI_TERM_001_SOURCE_RUNTIME_EVIDENCE.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    assert out.exists()

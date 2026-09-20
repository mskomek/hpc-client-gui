"""W21 — Terminal lifecycle, threading and cleanup regressions.

DEF-W21-001 (HPC-W05-LIFE-022/068, HPC-W05-TODO-LIFECYCLE-NATIVE-002):
closing a WebView terminal while wx native teardown is already in progress
must not explicitly Destroy the native WebView2 controller (shutdown AV).

DEF-W21-002 (HPC-W05-LIFE-014/015/022/066/068): the legacy TextCtrl
fallback output path must drop post-close output and stale-generation output
after reconnect, mirroring the canonical WebView generation guard.

Real code exercised: WxTerminalWebViewPanel.close/Destroy/set_ssh,
wx_terminal.build_terminal_panel fallback render/subscriber/set_ssh/close,
WxLifecycleController.shutdown, _controller_disconnect_cb.
Mocked boundary: SSH transport (FakeSSH) and the JS sink (_run_js capture)
for WebView tests; the widgets, dispatch, guards and labels are real.
What these tests do NOT prove: actual xterm rendering, a live SSH server
(EXTERNAL covers the live loopback separately), or a real OS-level
WebView2 crash — the shutdown test proves the Destroy call contract that
removes the AV trigger instead.
"""

import pytest

wx = pytest.importorskip("wx")
pytestmark = pytest.mark.wx

from hpc_gui.wx_terminal_webview import _is_webview_available


def _run_subprocess_test(code_str, timeout=30):
    import os
    import subprocess
    import sys

    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    return subprocess.run(
        [sys.executable, "-c", code_str],
        capture_output=True, text=True, timeout=timeout, env=env,
    )


_SETUP = """
import sys
sys.path.insert(0, "src")
import wx

class FakeSSH:
    def __init__(self, user="", host=""):
        self.sent = []
        self._wx_output_subscribers = []
        self._username = user
        self._hostname = host
    def send_shell_input(self, d):
        self.sent.append(d)
        return True
    def resize_shell_pty(self, c, r):
        pass

app = wx.App.Get()
if app is None:
    app = wx.App(False)
"""


@pytest.mark.gui
@pytest.mark.subprocess
@pytest.mark.semantic
def test_w21_close_skips_native_destroy_while_being_deleted():
    """DEF-W21-001 / REQ-LIFE-022/068: no explicit Destroy mid-teardown."""
    if not _is_webview_available():
        pytest.skip("WebView backend unavailable")
    from hpc_gui.wx_terminal_webview import WxTerminalWebViewPanel

    code = _SETUP + """
from hpc_gui.wx_terminal_webview import WxTerminalWebViewPanel
frame = wx.Frame(None, size=(900, 600))

# Panel under native teardown: close must Stop (best-effort) but never Destroy.
panel = WxTerminalWebViewPanel(frame, ssh=FakeSSH())
webview = panel._webview
assert webview is not None
stops, destroys = [], []
webview.Stop = lambda *a, **k: stops.append("Stop")
webview.Destroy = lambda *a, **k: destroys.append("Destroy")
panel.IsBeingDeleted = lambda: True
panel.close()
assert stops == ["Stop"], stops
assert destroys == [], f"Destroy during native teardown risks WebView2 AV: {destroys}"
assert panel._webview is None and panel._is_parity is False
# Idempotent: second close is a no-op (no additional native calls).
panel.close()
assert stops == ["Stop"] and destroys == []

# Normal close still releases the native controller exactly once.
panel2 = WxTerminalWebViewPanel(frame, ssh=FakeSSH())
webview2 = panel2._webview
stops2, destroys2 = [], []
webview2.Stop = lambda *a, **k: stops2.append("Stop")
webview2.Destroy = lambda *a, **k: destroys2.append("Destroy")
panel2.close()
assert stops2 == ["Stop"] and destroys2 == ["Destroy"], (stops2, destroys2)
frame.Destroy()
import os; os._exit(0)
"""
    result = _run_subprocess_test(code)
    assert result.returncode == 0, f"subprocess failed: {result.stdout}\n{result.stderr}"


@pytest.mark.gui
@pytest.mark.subprocess
@pytest.mark.semantic
def test_w21_double_close_and_destroy_is_idempotent():
    """REQ-LIFE-015/022: close/close/Destroy/frame-destroy never raises."""
    if not _is_webview_available():
        pytest.skip("WebView backend unavailable")
    code = _SETUP + """
from hpc_gui.wx_terminal_webview import WxTerminalWebViewPanel
frame = wx.Frame(None, size=(900, 600))
panel = WxTerminalWebViewPanel(frame, ssh=FakeSSH())
panel.close()
panel.close()
panel.Destroy()
frame.Destroy()
import os; os._exit(0)
"""
    result = _run_subprocess_test(code)
    assert result.returncode == 0, f"subprocess failed: {result.stdout}\n{result.stderr}"


@pytest.mark.gui
@pytest.mark.subprocess
@pytest.mark.semantic
def test_w21_disconnect_visible_and_reconnect_fresh_identity():
    """REQ-LIFE-014: disconnect is visible; reconnect mints fresh identity."""
    if not _is_webview_available():
        pytest.skip("WebView backend unavailable")
    code = _SETUP + """
from hpc_gui.wx_terminal_webview import WxTerminalWebViewPanel
frame = wx.Frame(None, size=(900, 600))
panel = WxTerminalWebViewPanel(frame, ssh=FakeSSH("u1", "h1"))
assert "u1@h1" in panel._identity_label.GetLabel(), panel._identity_label.GetLabel()
gen_before = panel._generation
# Disconnect: write path neutralized, status + identity cleared visibly.
panel.set_ssh(None)
assert panel._status_label.GetLabel() != "", "disconnect must stay visible"
assert panel._identity_label.GetLabel() == "", "identity must clear on disconnect"
assert panel._handle_input("echo nowhere") is False
# Reconnect: fresh generation (stale callbacks rejected) + new identity.
panel.set_ssh(FakeSSH("u2", "h2"))
assert panel._generation != gen_before, "reconnect must mint a fresh generation"
assert "u2@h2" in panel._identity_label.GetLabel(), panel._identity_label.GetLabel()
assert panel._handle_input("echo back") is True
panel.close()
frame.Destroy()
import os; os._exit(0)
"""
    result = _run_subprocess_test(code)
    assert result.returncode == 0, f"subprocess failed: {result.stdout}\n{result.stderr}"


@pytest.mark.gui
@pytest.mark.subprocess
@pytest.mark.semantic
def test_w21_fallback_render_after_close_is_dropped():
    """DEF-W21-002 / REQ-LIFE-068: fallback drops post-close output."""
    code = _SETUP + """
import hpc_gui.wx_terminal_webview as webmod
webmod._is_webview_available = lambda: False
from hpc_gui.wx_terminal import build_terminal_panel
frame = wx.Frame(None, size=(900, 600))
ssh = FakeSSH()
panel = build_terminal_panel(frame, ssh=ssh)
render = panel._wx_terminal_render
text = panel._wx_terminal_controls["output"]
render("hello-A")
assert text.GetValue() == "hello-A", repr(text.GetValue())
# Queue output, then close before the GUI thread dispatches it.
sub = ssh._wx_output_subscribers[0]
sub("queued-then-closed")
panel._wx_terminal_close()
# Pump the event loop so the queued CallAfter would fire if unguarded.
import time
start = time.monotonic()
while time.monotonic() - start < 0.5:
    try:
        wx.Yield()
    except Exception:
        pass
    time.sleep(0.05)
assert text.GetValue() == "hello-A", f"post-close output leaked: {text.GetValue()!r}"
# Direct renders after close are dropped as well.
render("late-direct")
assert text.GetValue() == "hello-A", f"direct post-close render leaked: {text.GetValue()!r}"
frame.Destroy()
import os; os._exit(0)
"""
    result = _run_subprocess_test(code)
    assert result.returncode == 0, f"subprocess failed: {result.stdout}\n{result.stderr}"


@pytest.mark.gui
@pytest.mark.subprocess
@pytest.mark.semantic
def test_w21_fallback_stale_generation_dropped_after_reconnect():
    """DEF-W21-002 / REQ-LIFE-066: fallback drops stale-session output."""
    code = _SETUP + """
import hpc_gui.wx_terminal_webview as webmod
webmod._is_webview_available = lambda: False
from hpc_gui.wx_terminal import build_terminal_panel
frame = wx.Frame(None, size=(900, 600))
sshA, sshB = FakeSSH(), FakeSSH()
panel = build_terminal_panel(frame, ssh=sshA)
text = panel._wx_terminal_controls["output"]
old_sub = sshA._wx_output_subscribers[0]
# Reconnect to session B, then deliver a stale callback from session A.
panel._wx_terminal_set_ssh(sshB)
old_sub("stale-from-A")
import time
start = time.monotonic()
while time.monotonic() - start < 0.5:
    try:
        wx.Yield()
    except Exception:
        pass
    time.sleep(0.05)
assert text.GetValue() == "", f"stale output rendered into new session: {text.GetValue()!r}"
# The live session still delivers.
new_sub = sshB._wx_output_subscribers[0]
new_sub("fresh-from-B")
start = time.monotonic()
while "fresh-from-B" not in text.GetValue() and time.monotonic() - start < 3:
    try:
        wx.Yield()
    except Exception:
        pass
    time.sleep(0.05)
assert "fresh-from-B" in text.GetValue(), repr(text.GetValue())
panel._wx_terminal_close()
frame.Destroy()
import os; os._exit(0)
"""
    result = _run_subprocess_test(code)
    assert result.returncode == 0, f"subprocess failed: {result.stdout}\n{result.stderr}"


@pytest.mark.gui
@pytest.mark.subprocess
@pytest.mark.semantic
def test_w21_fallback_repeated_reconnect_cleans_all_subscribers():
    """DEF-W21-AUDIT-001 / REQ-LIFE-022/066/068: close owns A/B/C callbacks."""
    code = _SETUP + """
import hpc_gui.wx_terminal_webview as webmod
webmod._is_webview_available = lambda: False
from hpc_gui.wx_terminal import build_terminal_panel
frame = wx.Frame(None, size=(900, 600))
ssh_a, ssh_b, ssh_c = FakeSSH(), FakeSSH(), FakeSSH()
panel = build_terminal_panel(frame, ssh=ssh_a)
panel._wx_terminal_set_ssh(ssh_b)
panel._wx_terminal_set_ssh(ssh_c)
assert [len(x._wx_output_subscribers) for x in (ssh_a, ssh_b, ssh_c)] == [0, 0, 1]
panel._wx_terminal_close()
assert [len(x._wx_output_subscribers) for x in (ssh_a, ssh_b, ssh_c)] == [0, 0, 0]
frame.Destroy()
import os; os._exit(0)
"""
    result = _run_subprocess_test(code)
    assert result.returncode == 0, f"subprocess failed: {result.stdout}\n{result.stderr}"


@pytest.mark.semantic
def test_w21_lifecycle_shutdown_is_reversed_idempotent_and_swallowing():
    """REQ-LIFE-015/022: shutdown runs reversed, once, swallowing failures."""
    from hpc_gui.wx_lifecycle import WxLifecycleController

    order = []

    def _boom():
        order.append("boom")
        raise RuntimeError("cleanup failure must not escape shutdown")

    lc = WxLifecycleController()
    lc.register_cleanup(lambda: order.append("first"))
    lc.register_cleanup(_boom)
    lc.register_cleanup(lambda: order.append("third"))
    lc.shutdown()
    assert order == ["third", "boom", "first"], order
    lc.shutdown()
    assert order == ["third", "boom", "first"], "second shutdown must be a no-op"
    assert lc.shutdown_started is True


@pytest.mark.semantic
def test_w21_disconnect_cb_leaves_connected_and_drops_stale():
    """REQ-LIFE-026/067: loss leaves CONNECTED; stale generation is dropped."""
    from hpc_gui.services.connection_controller import ConnectionController
    from hpc_gui.wx_connection import _controller_disconnect_cb

    hook_calls = []

    class Model:
        def __init__(self):
            self.controller = ConnectionController()
            self._session_invalidated_hook = lambda: hook_calls.append("hook")

    # Current-owner transport loss: controller must leave CONNECTED.
    model = Model()
    live_ssh = object()
    model.controller.finish({"ssh": live_ssh, "profile_name": "lab"})
    assert model.controller.state.value == "connected"
    cb = _controller_disconnect_cb(model, lambda: live_ssh)
    cb("transport lost")
    assert model.controller.state.value != "connected", model.controller.state.value
    assert model.controller.session is None, "dead session ownership must be cleaned"
    assert hook_calls == ["hook"], "shell invalidation must observe the loss"

    # Stale callback from a superseded session: the new session survives.
    model2 = Model()
    old_ssh, new_ssh = object(), object()
    model2.controller.finish({"ssh": new_ssh, "profile_name": "lab-B"})
    stale_cb = _controller_disconnect_cb(model2, lambda: old_ssh)
    stale_cb("late death of superseded transport")
    assert model2.controller.state.value == "connected", model2.controller.state.value
    assert model2.controller.session is not None
    assert hook_calls == ["hook"], "stale callback must not invalidate the shell"

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
pytestmark = pytest.mark.wx

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

    app = wx.App.Get()
    if app is None:
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



"""Real wx/WebKitGTK parent-close regression in isolated GUI processes.

A passing fake-WebView contract cannot establish that wx.App.MainLoop exits
after the native WebView child is destroyed. This test never uses os._exit().
"""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys
import textwrap

import pytest

from support.subprocess_environment import project_python_environment


pytestmark = [pytest.mark.gui, pytest.mark.subprocess, pytest.mark.regression]


def test_native_webview_parent_close_returns_mainloop():
    if sys.platform.startswith("linux") and not os.environ.get("DISPLAY"):
        pytest.skip("real X display required; run under Xvfb or GNOME")

    script = textwrap.dedent(
        """
        import wx
        import wx.html2
        from hpc_gui.wx_terminal_webview import WxTerminalWebViewPanel

        app = wx.App(False)
        frame = wx.Frame(None, title="native-close-probe", size=(840, 540))
        panel = WxTerminalWebViewPanel(frame)
        assert panel._webview is not None, "native WebView unavailable"
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(panel, 1, wx.EXPAND)
        frame.SetSizer(root)
        frame.Layout()
        app.SetTopWindow(frame)
        frame.Show()

        wx.CallLater(600, frame.Close)
        app.MainLoop()
        assert panel._closed, "panel did not receive native destroy"
        print("NATIVE_WEBVIEW_MAINLOOP_EXITED", flush=True)
        """
    )
    env = project_python_environment(pathlib.Path(__file__).resolve().parents[1])

    for attempt in range(1, 4):
        try:
            result = subprocess.run(
                [sys.executable, "-c", script],
                capture_output=True,
                text=True,
                env=env,
                timeout=12,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            pytest.fail(
                f"native WebView parent close timed out (attempt {attempt}/3); "
                f"partial stdout={exc.stdout!r}, stderr={exc.stderr!r}"
            )
        assert result.returncode == 0, (
            f"native WebView close failed (attempt {attempt}/3) "
            f"exit={result.returncode}, stdout={result.stdout!r}, "
            f"stderr={result.stderr!r}"
        )
        assert "NATIVE_WEBVIEW_MAINLOOP_EXITED" in result.stdout

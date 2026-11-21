"""Native GTK/WebKit integration of the production main-frame exit policy.

Unlike standalone wx.Frame defaults, the production shell binds EVT_CLOSE to
run its teardown and calls Destroy; the PR #78 policy must then observe the
actual main frame's native destruction and exit MainLoop.

This subprocess test intentionally does not use os._exit or forced-timeout PASS.
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


def test_production_native_destroy_event_exits_real_webview_mainloop():
    if sys.platform.startswith("linux") and not os.environ.get("DISPLAY"):
        pytest.skip("X display unavailable")

    script = textwrap.dedent(
        """
        import wx
        from hpc_gui.wx_application import install_main_frame_exit_policy
        from hpc_gui.wx_terminal_webview import WxTerminalWebViewPanel

        app = wx.App(False)
        frame = wx.Frame(None, title="production-exit-policy-webview", size=(840, 540))
        panel = WxTerminalWebViewPanel(frame)
        assert panel._webview is not None, "WebView backend unavailable"
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(panel, 1, wx.EXPAND)
        frame.SetSizer(sizer)
        frame.Layout()

        app.SetTopWindow(frame)
        install_main_frame_exit_policy(wx, app, frame)
        print("POLICY: installed", flush=True)

        def close(event):
            if event.GetVeto():
                print("POLICY: explicit veto", flush=True)
                return
            print("POLICY: destroying frame", flush=True)
            print(f"POLICY: destroy_return={frame.Destroy()}", flush=True)

        frame.Bind(wx.EVT_CLOSE, close)
        frame.Show()
        wx.CallLater(600, frame.Close)
        app.MainLoop()

        assert panel._closed, "native terminal cleanup was not called"
        print("PRODUCTION_POLICY_MAINLOOP_EXITED", flush=True)
        """
    )
    env = project_python_environment(pathlib.Path(__file__).resolve().parents[1])
    try:
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            env=env,
            timeout=15,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        pytest.fail(
            f"production policy timed out: stdout={exc.stdout!r} "
            f"stderr={exc.stderr!r}"
        )
    assert result.returncode == 0, (
        f"production policy exit={result.returncode}, "
        f"stdout={result.stdout!r}, stderr={result.stderr!r}"
    )
    assert "PRODUCTION_POLICY_MAINLOOP_EXITED" in result.stdout

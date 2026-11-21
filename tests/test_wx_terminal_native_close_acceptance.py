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
        import faulthandler
        import wx
        import wx.html2

        faulthandler.enable()
        faulthandler.dump_traceback_later(7, repeat=False)
        from hpc_gui.wx_terminal_webview import WxTerminalWebViewPanel

        app = wx.App(False)
        frame = wx.Frame(None, title="native-close-probe", size=(840, 540))
        panel = WxTerminalWebViewPanel(frame)
        print("NATIVE_STAGE: constructed", flush=True)
        assert panel._webview is not None, "native WebView unavailable"
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(panel, 1, wx.EXPAND)
        frame.SetSizer(root)
        frame.Layout()
        app.SetTopWindow(frame)

        def observe_destroy(event):
            try:
                own_window = event.GetWindow() is frame
            except Exception:
                own_window = False
            print(f"NATIVE_STAGE: frame_destroy_event own={own_window}", flush=True)
            event.Skip()

        frame.Bind(wx.EVT_WINDOW_DESTROY, observe_destroy)
        frame.Show()
        print("NATIVE_STAGE: shown", flush=True)

        def close_frame():
            print("NATIVE_STAGE: close_begin", flush=True)
            frame.Close()
            print("NATIVE_STAGE: close_returned", flush=True)

        def inspect_after_close():
            try:
                top_count = len(wx.GetTopLevelWindows())
            except Exception:
                top_count = -1
            print(
                f"NATIVE_STAGE: after_close panel_closed={panel._closed} "
                f"top_windows={top_count}",
                flush=True,
            )

        wx.CallLater(600, close_frame)
        wx.CallLater(3000, inspect_after_close)
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

def test_blank_native_wx_frame_exits_mainloop():
    if sys.platform.startswith("linux") and not os.environ.get("DISPLAY"):
        pytest.skip("real X display required; run under Xvfb or GNOME")

    code = textwrap.dedent(
        """
        import wx
        app = wx.App(False)
        frame = wx.Frame(None, title="blank-close-control")
        app.SetTopWindow(frame)
        frame.Show()
        wx.CallLater(600, frame.Close)
        app.MainLoop()
        print("BLANK_MAINLOOP_EXITED", flush=True)
        """
    )
    env = project_python_environment(pathlib.Path(__file__).resolve().parents[1])
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        env=env,
        timeout=12,
        check=False,
    )
    assert result.returncode == 0, (
        f"blank wx control exit={result.returncode}; "
        f"stdout={result.stdout!r}, stderr={result.stderr!r}"
    )
    assert "BLANK_MAINLOOP_EXITED" in result.stdout

"""Shared utilities for the focused wx terminal WebView test modules."""
from __future__ import annotations

import os
import pathlib
import subprocess
import sys
import time

import wx

ASSETS = pathlib.Path(__file__).parents[1] / "src" / "hpc_gui" / "assets" / "terminal"


def _fake_ssh():
    class Fake:
        def __init__(self):
            self.sent = []
            self.resizes = []
            self._wx_output_subscribers = []

        def send_shell_input(self, data):
            self.sent.append(data)
            return True

        def resize_shell_pty(self, cols, rows):
            self.resizes.append((cols, rows))

    return Fake()


def _wait_for_ready(panel, timeout=6):
    """Run wx's native loop until the WebView bridge reports ready or times out."""
    if getattr(panel, "_ready", False):
        return True
    deadline = time.monotonic() + timeout
    if sys.platform.startswith("linux"):
        while not getattr(panel, "_ready", False) and time.monotonic() < deadline:
            wx.Yield()
            time.sleep(0.05)
        return bool(getattr(panel, "_ready", False))
    app = wx.App.Get()
    if app is None:
        return False

    def check_ready():
        if getattr(panel, "_ready", False) or time.monotonic() >= deadline:
            app.ExitMainLoop()
            return
        wx.CallLater(25, check_ready)

    wx.CallAfter(check_ready)
    app.MainLoop()
    return bool(getattr(panel, "_ready", False))


def _show_frame_with_panel(frame, panel):
    """Show and lay out the panel so WebView sizing and fit are realistic."""
    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(panel, 1, wx.EXPAND)
    frame.SetSizer(sizer)
    frame.Layout()
    frame.Show()


def _run_subprocess_test(code_str, timeout=15, env=None):
    """Run an isolated wx test with project and test helpers on PYTHONPATH."""
    child_env = dict(os.environ if env is None else env)
    child_env["PYTHONPATH"] = os.pathsep.join(
        ("src", "tests", child_env.get("PYTHONPATH", ""))
    )
    return subprocess.run(
        [sys.executable, "-c", code_str],
        capture_output=True,
        text=True,
        timeout=timeout,
        env=child_env,
    )

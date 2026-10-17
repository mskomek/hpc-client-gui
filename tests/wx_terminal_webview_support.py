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
    """Pump wx events until the WebView bridge reports ready."""
    start = time.monotonic()
    loop = wx.GUIEventLoop()
    while time.monotonic() - start < timeout:
        if getattr(panel, "_ready", False):
            return True
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
    return bool(getattr(panel, "_ready", False))


def _show_frame_with_panel(frame, panel):
    """Show and lay out the panel so WebView sizing and fit are realistic."""
    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(panel, 1, wx.EXPAND)
    frame.SetSizer(sizer)
    frame.Layout()
    frame.Show()
    wx.Yield()
    time.sleep(0.05)
    wx.Yield()


def _run_subprocess_test(code_str, timeout=15):
    """Run an isolated wx test with the project source on PYTHONPATH."""
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    return subprocess.run(
        [sys.executable, "-c", code_str],
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )

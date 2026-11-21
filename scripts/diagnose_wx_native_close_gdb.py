"""Bounded native stack capture for a hanging wxGTK terminal WebView shutdown.

This file is a diagnostic *inferior*, not an application exit workaround.
Run under gdb with "handle SIGALRM stop print nopass"; SIGALRM is raised after
the close attempt if the native event loop has not naturally returned.
No credentials, network connections, SSH profiles, or persistent user data.
"""

from __future__ import annotations

import signal
import sys

import wx

from hpc_gui.wx_application import install_main_frame_exit_policy
from hpc_gui.wx_terminal_webview import WxTerminalWebViewPanel
from hpc_gui.wx_shell_smoke_finalize import _frame_destroyed


def main() -> int:
    app = wx.App(False)
    frame = wx.Frame(None, title="gdb-webview-close-probe", size=(840, 540))
    panel = WxTerminalWebViewPanel(frame)
    if panel._webview is None:
        print("GDB_PROBE: WebView unavailable", flush=True)
        return 3
    size = wx.BoxSizer(wx.VERTICAL)
    size.Add(panel, 1, wx.EXPAND)
    frame.SetSizer(size)
    frame.Layout()
    app.SetTopWindow(frame)
    install_main_frame_exit_policy(wx, app, frame)

    def close(event):
        if event.CanVeto() and event.GetVeto():
            print("GDB_PROBE: close vetoed", flush=True)
            return
        print("GDB_PROBE: destroying", flush=True)
        frame._wx_shell_destroy_invoked = True
        print(f"GDB_PROBE: destroy_return={frame.Destroy()}", flush=True)

    frame.Bind(wx.EVT_CLOSE, close)

    def inspect():
        print(
            f"GDB_PROBE: panel_closed={panel._closed} "
            f"native_deleted={_frame_destroyed(wx, frame)} "
            f"top_count={len(wx.GetTopLevelWindows())}",
            flush=True,
        )

    frame.Show()
    print("GDB_PROBE: frame_shown", flush=True)
    # A deliberate fatal signal with debugger interception is diagnostic,
    # NOT a success path or a replacement for native event-loop shutdown.
    signal.alarm(9)
    wx.CallLater(600, frame.Close)
    wx.CallLater(2500, inspect)
    app.MainLoop()
    signal.alarm(0)
    print(f"GDB_PROBE: natural_mainloop_exit panel_closed={panel._closed}", flush=True)
    return 0 if panel._closed else 2


if __name__ == "__main__":
    sys.exit(main())

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
        def exit_policy():
            getter = getattr(app, "GetExitOnFrameDelete", None)
            return getter() if callable(getter) else "not-exposed"

        print(f"NATIVE_STAGE: exit_policy_before={exit_policy()}", flush=True)
        panel = WxTerminalWebViewPanel(frame)
        print(f"NATIVE_STAGE: exit_policy_after={exit_policy()}", flush=True)
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

        def observe_close(event):
            print(
                f"NATIVE_STAGE: close_event_begin can_veto={event.CanVeto()} "
                f"vetoed={event.GetVeto()}",
                flush=True,
            )
            event.Skip()
            print(
                f"NATIVE_STAGE: close_event_skip vetoed={event.GetVeto()}",
                flush=True,
            )

        frame.Bind(wx.EVT_WINDOW_DESTROY, observe_destroy)
        frame.Bind(wx.EVT_CLOSE, observe_close)
        frame.Show()
        print("NATIVE_STAGE: shown", flush=True)

        def close_frame():
            print("NATIVE_STAGE: close_begin", flush=True)
            accepted = frame.Close()
            print(f"NATIVE_STAGE: close_returned accepted={accepted}", flush=True)

        def inspect_after_close():
            try:
                windows = wx.GetTopLevelWindows()
                top_count = len(windows)
                description = [(w.GetName(), w.IsShown(), w.IsBeingDeleted()) for w in windows]
            except Exception:
                top_count, description = -1, []
            print(
                f"NATIVE_STAGE: after_close panel_closed={panel._closed} "
                f"top_windows={top_count} frame_shown={frame.IsShown()} "
                f"top_detail={description!r}",
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


def test_native_webview_direct_destroy_exits_mainloop():
    if sys.platform.startswith("linux") and not os.environ.get("DISPLAY"):
        pytest.skip("real X display required; run under Xvfb or GNOME")

    script = textwrap.dedent(
        """
        import wx
        import wx.html2
        from hpc_gui.wx_terminal_webview import WxTerminalWebViewPanel

        app = wx.App(False)
        frame = wx.Frame(None, title="native-direct-destroy-control", size=(840, 540))
        panel = WxTerminalWebViewPanel(frame)
        getter = getattr(app, "GetExitOnFrameDelete", None)
        print(f"NATIVE_STAGE: exit_policy_direct={getter() if callable(getter) else 'not-exposed'}", flush=True)
        assert panel._webview is not None, "native WebView unavailable"
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(panel, 1, wx.EXPAND)
        frame.SetSizer(sizer)
        frame.Layout()
        app.SetTopWindow(frame)
        frame.Show()

        def destroy_now():
            print("NATIVE_STAGE: force_destroy_begin", flush=True)
            result = frame.Destroy()
            print(f"NATIVE_STAGE: force_destroy_returned {result}", flush=True)

        def inspect_after_destroy():
            try:
                windows = wx.GetTopLevelWindows()
                details = [(w.GetName(), w.IsShown(), w.IsBeingDeleted()) for w in windows]
            except Exception as exc:
                details = f"error:{type(exc).__name__}"
            print(
                f"NATIVE_STAGE: after_force_destroy panel_closed={panel._closed} "
                f"top_detail={details!r}",
                flush=True,
            )

        wx.CallLater(600, destroy_now)
        wx.CallLater(2500, inspect_after_destroy)
        app.MainLoop()
        assert panel._closed, "panel destroy callback was not received"
        print("NATIVE_DIRECT_DESTROY_EXITED", flush=True)
        """
    )
    env = project_python_environment(pathlib.Path(__file__).resolve().parents[1])
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
            "direct frame Destroy did not finish native MainLoop: "
            f"stdout={exc.stdout!r} stderr={exc.stderr!r}"
        )
    assert result.returncode == 0, (
        f"direct Destroy exit={result.returncode}, stdout={result.stdout!r}, "
        f"stderr={result.stderr!r}"
    )
    assert "NATIVE_DIRECT_DESTROY_EXITED" in result.stdout


def test_minimal_webview_frame_close_returns_mainloop():
    """Control case distinguishes native WebKitGTK backend from panel lifecycle."""
    if sys.platform.startswith("linux") and not os.environ.get("DISPLAY"):
        pytest.skip("real X display required; run under Xvfb or GNOME")

    code = textwrap.dedent(
        """
        import wx
        import wx.html2
        app = wx.App(False)
        frame = wx.Frame(None, title="minimal-webview-control")
        view = wx.html2.WebView.New(frame)
        assert view is not None
        frame.SetSizer(wx.BoxSizer(wx.VERTICAL))
        frame.GetSizer().Add(view, 1, wx.EXPAND)
        frame.Layout()
        app.SetTopWindow(frame)
        frame.Show()
        def observe(event):
            print(
                f"MINIMAL: close_event can_veto={event.CanVeto()} "
                f"vetoed={event.GetVeto()}",
                flush=True,
            )
            event.Skip()
        frame.Bind(wx.EVT_CLOSE, observe)
        def close_now():
            print(f"MINIMAL: Close return={frame.Close()}", flush=True)
        wx.CallLater(600, close_now)
        app.MainLoop()
        print("MINIMAL_WEBVIEW_EXITED", flush=True)
        """
    )
    env = project_python_environment(pathlib.Path(__file__).resolve().parents[1])
    try:
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            env=env,
            timeout=12,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        pytest.fail(
            f"minimal WebView control hung: stdout={exc.stdout!r} stderr={exc.stderr!r}"
        )
    assert result.returncode == 0 and "MINIMAL_WEBVIEW_EXITED" in result.stdout, (
        f"minimal WebView exit={result.returncode}: "
        f"stdout={result.stdout!r}, stderr={result.stderr!r}"
    )


def test_terminal_fallback_panel_exits_mainloop():
    """Control: the terminal panel itself, without a native WebKit child."""
    if sys.platform.startswith("linux") and not os.environ.get("DISPLAY"):
        pytest.skip("real X display required; run under Xvfb or GNOME")

    script = textwrap.dedent(
        """
        import wx
        import hpc_gui.wx_terminal_webview as module
        module._is_webview_available = lambda: False

        app = wx.App(False)
        frame = wx.Frame(None, title="terminal-fallback-control")
        panel = module.WxTerminalWebViewPanel(frame)
        assert panel._webview is None
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(panel, 1, wx.EXPAND)
        frame.SetSizer(sizer)
        app.SetTopWindow(frame)
        frame.Show()

        def close_now():
            print(f"FALLBACK: close_return={frame.Close()}", flush=True)

        wx.CallLater(600, close_now)
        app.MainLoop()
        assert panel._closed, "fallback panel did not close"
        print("FALLBACK_MAINLOOP_EXITED", flush=True)
        """
    )
    env = project_python_environment(pathlib.Path(__file__).resolve().parents[1])
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
            f"fallback panel control hung: stdout={exc.stdout!r} stderr={exc.stderr!r}"
        )
    assert result.returncode == 0 and "FALLBACK_MAINLOOP_EXITED" in result.stdout, (
        f"fallback panel exit={result.returncode}, stdout={result.stdout!r}, "
        f"stderr={result.stderr!r}"
    )

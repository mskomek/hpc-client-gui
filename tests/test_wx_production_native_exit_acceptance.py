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
        from hpc_gui.wx_shell_smoke_finalize import _frame_destroyed

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

        def describe_window(w):
            if w is None:
                return "none"
            try:
                return (
                    f"{type(w).__name__}(name={w.GetName()!r},"
                    f"id={w.GetId()},frame={w is frame},panel={w is panel})"
                )
            except Exception as exc:
                return f"{type(w).__name__}(unavailable={type(exc).__name__})"

        def trace_destroy(event):
            try:
                native_target = event.GetWindow()
            except Exception as exc:
                native_target = None
                print(f"POLICY: GetWindow_error={type(exc).__name__}", flush=True)
            try:
                event_object = event.GetEventObject()
            except Exception:
                event_object = None
            try:
                source_id = native_target.GetId() if native_target is not None else None
                parent = native_target.GetParent() if native_target is not None else None
                parent_is_none = parent is None
                top_level = isinstance(native_target, wx.TopLevelWindow)
                frame_id = frame.GetId()
            except Exception as exc:
                source_id = frame_id = None
                parent_is_none = top_level = False
                print(f"POLICY: source_fields_error={type(exc).__name__}", flush=True)
            print(
                f"POLICY: destroy_event source={describe_window(native_target)} "
                f"event_object={describe_window(event_object)} "
                f"source_id={source_id} frame_id={frame_id} "
                f"is_top_level={top_level} parent_none={parent_is_none}",
                flush=True,
            )
            event.Skip()

        frame.Bind(wx.EVT_WINDOW_DESTROY, trace_destroy)

        def close(event):
            if event.GetVeto():
                print("POLICY: explicit veto", flush=True)
                return
            print("POLICY: destroying frame", flush=True)
            frame._wx_shell_destroy_invoked = True
            print(f"POLICY: destroy_return={frame.Destroy()}", flush=True)

        frame.Bind(wx.EVT_CLOSE, close)
        frame.Show()

        def inspect_after_destroy():
            try:
                top_windows = [w.GetName() for w in wx.GetTopLevelWindows()]
            except Exception as exc:
                top_windows = [type(exc).__name__]
            print(
                f"POLICY: after_destroy panel_closed={panel._closed} "
                f"top_windows={top_windows!r} "
                f"frame_native_deleted={_frame_destroyed(wx, frame)} "
                f"exit_policy_error={getattr(frame, '_wx_shell_exit_loop_error_type', '')}",
                flush=True,
            )

        wx.CallLater(600, frame.Close)
        wx.CallLater(2500, inspect_after_destroy)
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

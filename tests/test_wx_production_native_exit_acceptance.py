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

        class AppWithExitEvidence(wx.App):
            def ExitMainLoop(self):
                try:
                    is_main_running = self.IsMainLoopRunning()
                except Exception as exc:
                    is_main_running = f"error:{type(exc).__name__}"
                try:
                    main = self.GetMainLoop()
                    main_loop_running = main.IsRunning() if main else None
                except Exception as exc:
                    main_loop_running = f"error:{type(exc).__name__}"
                try:
                    active = wx.EventLoopBase.GetActive()
                    active_running = active.IsRunning() if active else None
                    active_is_main = active is main
                    active_type = type(active).__name__ if active else None
                    main_type = type(main).__name__ if main else None
                except Exception as exc:
                    active_running = f"error:{type(exc).__name__}"
                    active_is_main = None
                    active_type = main_type = None
                print(
                    f"POLICY: ExitMainLoop_called main_running={is_main_running} "
                    f"main_loop_running={main_loop_running} active_running={active_running} "
                    f"active_is_main={active_is_main} active_type={active_type} main_type={main_type}",
                    flush=True,
                )
                outcome = super().ExitMainLoop()
                print(f"POLICY: ExitMainLoop_return={outcome!r}", flush=True)
                return outcome

        app = AppWithExitEvidence(False)
        frame = wx.Frame(None, title="production-exit-policy-webview", size=(840, 540))
        panel = WxTerminalWebViewPanel(frame)
        assert panel._webview is not None, "WebView backend unavailable"
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(panel, 1, wx.EXPAND)
        frame.SetSizer(sizer)
        frame.Layout()

        app.SetTopWindow(frame)
        install_main_frame_exit_policy(wx, app, frame)
        cached_frame_id = frame.GetId()
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
            except Exception as exc:
                source_id = None
                print(f"POLICY: GetId_error={type(exc).__name__}", flush=True)
            try:
                parent = native_target.GetParent() if native_target is not None else None
                parent_state = "none" if parent is None else "non-null"
            except Exception as exc:
                parent_state = f"error:{type(exc).__name__}"
            try:
                top_level = isinstance(native_target, wx.TopLevelWindow)
            except Exception as exc:
                top_level = False
                print(f"POLICY: type_check_error={type(exc).__name__}", flush=True)
            print(
                f"POLICY: destroy_event source={describe_window(native_target)} "
                f"event_object={describe_window(event_object)} "
                f"source_id={source_id} cached_frame_id={cached_frame_id} "
                f"is_top_level={top_level} parent={parent_state}",
                flush=True,
            )
            event.Skip()

        # The application policy owns the sole native destroy-event handler.
        # A second Bind here can change wxGTK dispatch order and mask the
        # callback being diagnosed; trace_destroy remains documented above.
        # The previous diagnostic run proved its source is a TopLevelWindow
        # alias with the cached main-frame ID and no parent.

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

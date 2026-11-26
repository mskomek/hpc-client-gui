"""wx application startup and event-loop lifecycle."""

from __future__ import annotations

import os

from hpc_gui.core.i18n import load_saved_language, system_default_language
from hpc_gui.wx_runtime import environment_without_qt_graphics


def install_main_frame_exit_policy(wx, app, frame) -> None:
    """Exit the production wx loop once the main window is natively gone.

    Destroy() returning is not proof the native HWND has been released. Queue
    ExitMainLoop from the real frame's destruction event instead of guessing
    a WebView2 callback delay. Child destroy events may propagate to frame.
    This hook intentionally is not installed for packaged smoke mode, whose
    test harness owns the event-loop lifecycle.
    """
    app.SetExitOnFrameDelete(True)
    exit_queued = False
    try:
        main_frame_id = frame.GetId()
    except Exception:
        main_frame_id = None

    def destroyed_main_frame(event) -> bool:
        # wxGTK can emit the same native frame as a fresh wx.TopLevelWindow
        # Python wrapper. Identity alone fails (observed in native W19); do
        # NOT use C++ wrapper equality during destruction.
        try:
            destroyed = event.GetWindow()
        except (AttributeError, RuntimeError):
            destroyed = None
        if destroyed is frame:
            return True
        if destroyed is None:
            try:
                destroyed = event.GetEventObject()
            except (AttributeError, RuntimeError):
                destroyed = None
        if destroyed is None or main_frame_id is None:
            return False
        top_level = getattr(wx, "TopLevelWindow", None)
        if top_level is None or not isinstance(destroyed, top_level):
            return False
        try:
            # wx assigns a unique native window ID at creation. Cache the
            # frame's ID while it is still valid: frame.GetId() itself can
            # fail after native wxGTK teardown.
            if destroyed.GetId() != main_frame_id:
                return False
        except (AttributeError, RuntimeError):
            return False
        try:
            # Reject owned top-level windows while their wrapper is live.
            # On wxGTK the destroy-event wrapper may already have a deleted
            # C++ parent; GetParent() then raises RuntimeError, even though
            # its native ID remains readable. Do not reject the main frame
            # solely because parent lookup is no longer possible.
            return destroyed.GetParent() is None
        except RuntimeError:
            return True
        except AttributeError:
            return False

    def on_destroyed(event):
        nonlocal exit_queued
        try:
            if destroyed_main_frame(event) and not exit_queued:
                try:
                    wx.CallAfter(app.ExitMainLoop)
                except Exception as exc:
                    frame._wx_shell_exit_loop_error_type = type(exc).__name__
                else:
                    exit_queued = True
        finally:
            try:
                event.Skip()
            except (AttributeError, RuntimeError):
                pass

    frame.Bind(wx.EVT_WINDOW_DESTROY, on_destroyed)


def activate_terminal_for_packaged_smoke(frame) -> bool:
    """Exercise the real notebook navigation before native WebView2 creation."""
    controls = getattr(frame, "_wx_shell_controls", {}) or {}
    notebook = controls.get("notebook")
    page = (controls.get("pages") or {}).get("NAV-TERMINAL", {}).get("page")
    if notebook is None or page is None:
        return False
    index = notebook.FindPage(page)
    if index < 0:
        return False
    notebook.SetSelection(index)
    return True


def run_wx_application(create_shell_frame, run_packaged_smoke) -> int:
    clean_environment = environment_without_qt_graphics()
    for name in set(os.environ) - set(clean_environment):
        os.environ.pop(name, None)
    load_saved_language(system_default_language())
    import wx

    app = wx.App(False)
    if os.environ.get("HPC_GUI_PACKAGED_SMOKE_OUTPUT"):
        app.SetAppName(
            os.environ.get("HPC_GUI_PACKAGED_SMOKE_APP_NAME")
            or f"hpc-client-gui-smoke-{os.getpid()}"
        )
        frame, _lifecycle, session_state = create_shell_frame(
            app, defer_terminal_webview=True
        )
        frame.Show()
        activate_terminal_for_packaged_smoke(frame)
        smoke_state = run_packaged_smoke(
            app,
            frame,
            session_state,
            os.environ["HPC_GUI_PACKAGED_SMOKE_OUTPUT"],
            _lifecycle,
        )
        app.MainLoop()
        return 0 if smoke_state["result"] == "PASS" else 1

    from hpc_gui.wx_crash_reporting import install_wx_crash_reporting

    report_previous_crash = install_wx_crash_reporting(app)
    profiles = []
    try:
        from hpc_gui.config.storage import load_profiles

        profiles = load_profiles()
    except Exception:
        pass

    splash = None
    try:
        from hpc_gui.wx_splash import create_startup_splash

        splash = create_startup_splash(None, profiles=profiles, pure_splash=True)
        splash.Show()
        app.SetTopWindow(splash)
    except Exception:
        splash = None

    def show_main_window() -> None:
        frame, _lifecycle, _session_state = create_shell_frame(
            app, defer_terminal_webview=True
        )
        if splash is not None:
            try:
                splash.Destroy()
            except Exception:
                pass
        app.SetTopWindow(frame)
        install_main_frame_exit_policy(wx, app, frame)
        from hpc_gui.wx_debug_telemetry import install_wx_debug_telemetry

        notebook = (getattr(frame, "_wx_shell_controls", {}) or {}).get("notebook")
        if notebook is not None:
            install_wx_debug_telemetry(frame, notebook)
        frame.Show()
        report_previous_crash(frame)
        try:
            frame.Raise()
        except Exception:
            pass

    startup_flow = None
    if splash is not None:
        try:
            from hpc_gui.wx_startup_flow import start_startup_flow

            startup_flow = start_startup_flow(app, splash, show_main_window)
        except Exception:
            show_main_window()
    else:
        show_main_window()

    # Keep the timer-driven startup controller alive until it opens the frame.
    _ = startup_flow
    app.MainLoop()
    return 0

"""wx application startup and event-loop lifecycle."""

from __future__ import annotations

import os

from hpc_gui.core.i18n import load_saved_language, system_default_language
from hpc_gui.wx_runtime import environment_without_qt_graphics


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
        smoke_state = run_packaged_smoke(
            app,
            frame,
            session_state,
            os.environ["HPC_GUI_PACKAGED_SMOKE_OUTPUT"],
            _lifecycle,
        )
        app.MainLoop()
        return 0 if smoke_state["result"] == "PASS" else 1

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
        frame.Show()
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

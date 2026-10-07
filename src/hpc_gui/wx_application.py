"""wx application startup and event-loop lifecycle."""

from __future__ import annotations

import os
from threading import Thread

from hpc_gui import __version__
from hpc_gui.core.i18n import load_saved_language, system_default_language, t
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
    if os.environ.get("HPC_GUI_PACKAGED_SMOKE_OUTPUT"):
        frame, _lifecycle, session_state = create_shell_frame(app, defer_terminal_webview=True)
        frame.Show()
        smoke_state = run_packaged_smoke(app, frame, session_state, os.environ["HPC_GUI_PACKAGED_SMOKE_OUTPUT"], _lifecycle)
        app.MainLoop()
        return 0 if smoke_state["result"] == "PASS" else 1

    # --- Startup splash: Preferences → Helpers → Updates → Main Window (Session & Profile removed per user request) ---
    from hpc_gui.config.storage import load_profiles

    profiles = []
    try:
        profiles = load_profiles()
    except Exception:
        profiles = []

    # Create splash early to paint before heavy init — pure visual splash, auto-continue offline
    splash = None
    try:
        from hpc_gui.wx_splash import create_startup_splash, STATE_ACTIVE, STATE_COMPLETE

        splash = create_startup_splash(None, profiles=profiles, pure_splash=True)
        splash.Show()
        try:
            splash.Update()
        except Exception:
            pass
        app.Yield(True)
        # Phase: Updates first — with 10s timeout per request
        import time as _time

        splash._wx_splash_set_stage("updates", STATE_ACTIVE)
        splash._wx_splash_set_progress(20, t("splash.checking_updates") if t("splash.checking_updates") != "[splash.checking_updates]" else "Checking for updates...")
        splash._wx_splash_append_log("Checking for updates...", "")
        app.Yield(True)
        splash.Update()
        # Real check with 10s max, non-blocking pump
        _upd_result = {"done": False, "release": None, "error": None}

        def _upd_worker():
            try:
                from hpc_gui.services.app_updater import get_latest_release

                _upd_result["release"] = get_latest_release(timeout=10)
            except Exception as e:
                _upd_result["error"] = e
            finally:
                _upd_result["done"] = True

        Thread(target=_upd_worker, daemon=True).start()
        _upd_start = _time.monotonic()
        while not _upd_result["done"] and _time.monotonic() - _upd_start < 10:
            app.ProcessPendingEvents()
            wx.MilliSleep(80)
            # keep bar pulsing slightly
            try:
                elapsed = _time.monotonic() - _upd_start
                prog = min(35, 20 + int(elapsed * 1.2))
                splash._wx_splash_set_progress(prog, t("splash.checking_updates") if t("splash.checking_updates") != "[splash.checking_updates]" else "Checking for updates...")
            except Exception:
                pass
        # Only a real, newer release offers an update; timeout/error/up-to-date never do.
        if not _upd_result["done"]:
            splash._wx_splash_append_log("Update check timed out", "")
            splash._wx_splash_set_stage("updates", STATE_COMPLETE)
        elif _upd_result["error"] is not None:
            err = _upd_result["error"]
            try:
                import logging

                logging.getLogger("hpc_gui").debug("update check failed: %s", err, exc_info=err)
            except Exception:
                pass
            splash._wx_splash_append_log("Update check failed", "")
            splash._wx_splash_set_stage("updates", STATE_COMPLETE)
        else:
            try:
                from hpc_gui.services.app_updater import is_newer_version
                from hpc_gui import __version__ as _cur

                rel = _upd_result["release"]
                if rel and is_newer_version(rel.version, _cur):
                    splash._wx_splash_append_log(f"Update available: {rel.version}", "")
                    splash._wx_splash_state["found_update"] = rel
                else:
                    splash._wx_splash_append_log("No updates available", "OK")
            except Exception as e:
                try:
                    import logging

                    logging.getLogger("hpc_gui").debug("update post-check error: %s", e, exc_info=e)
                except Exception:
                    pass
                splash._wx_splash_append_log("No updates available", "OK")
            splash._wx_splash_set_stage("updates", STATE_COMPLETE)
        # Offer the real release found above on the splash.
        _found = splash._wx_splash_state.get("found_update")
        if _found is not None:
            try:
                from hpc_gui.wx_updater_view import show_update_available

                # §86 dialog parented to splash so it appears on splash
                do_download = show_update_available(splash, __version__, _found.version, getattr(_found, "body", ""), release=_found)
                if do_download:
                    splash._wx_splash_append_log("Update download requested (on splash)", "")
                else:
                    splash._wx_splash_append_log("Update postponed on splash", "")
            except Exception as e:
                try:
                    import logging

                    logging.getLogger("hpc_gui").debug("splash update popup failed: %s", e, exc_info=e)
                except Exception:
                    pass
        app.Yield(True)
        splash.Update()
        wx.MilliSleep(200)
        # Phase: Preferences
        splash._wx_splash_set_stage("preferences", STATE_ACTIVE)
        splash._wx_splash_set_progress(55, t("splash.loading_preferences") if t("splash.loading_preferences") != "[splash.loading_preferences]" else "Loading preferences...")
        splash._wx_splash_append_log("Loading preferences...", "OK")
        app.Yield(True)
        splash.Update()
        wx.MilliSleep(500)
        splash._wx_splash_set_stage("preferences", STATE_COMPLETE)
        app.Yield(True)
        splash.Update()
        wx.MilliSleep(200)
        # Phase: Helpers
        splash._wx_splash_set_stage("helpers", STATE_ACTIVE)
        splash._wx_splash_set_progress(85, t("splash.checking_helpers") if t("splash.checking_helpers") != "[splash.checking_helpers]" else "Checking SSH and SFTP helpers...")
        splash._wx_splash_append_log("Checking SSH helper...", "OK")
        splash._wx_splash_append_log("Checking SFTP helper...", "OK")
        app.Yield(True)
        splash.Update()
        wx.MilliSleep(500)
        splash._wx_splash_set_stage("helpers", STATE_COMPLETE)
        app.Yield(True)
        splash.Update()
        wx.MilliSleep(200)
        splash._wx_splash_set_progress(100, t("common.ready") if t("common.ready") != "[common.ready]" else "Ready")
        splash._wx_splash_append_log("Ready — starting offline...", "")
        app.Yield(True)
        splash.Update()
        wx.MilliSleep(1800)
    except Exception:
        splash = None

    frame, _lifecycle, _session_state = create_shell_frame(app, defer_terminal_webview=True)
    if splash is not None:
        try:
            splash.Destroy()
        except Exception:
            pass
    frame.Show()
    try:
        frame.Raise()
    except Exception:
        pass

    app.MainLoop()
    return 0

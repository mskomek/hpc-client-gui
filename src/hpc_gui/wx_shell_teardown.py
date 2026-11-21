"""Shell close handler extracted from wx_shell_frame (W65 architecture split).

The handler is pure composition: it sequences page teardown, chrome close,
bounded lifecycle shutdown and the final Destroy. Keeping it in its own module
leaves the frame builder under the 500-line limit without changing behaviour.
"""

from __future__ import annotations

from hpc_gui.core.i18n import unsubscribe_language_change
from hpc_gui.wx_terminal_diagnostics import record_terminal_event


def build_shell_close_handler(
    wx,
    frame,
    notebook,
    lifecycle,
    page_controls,
    chrome_windows,
    shell_ref,
    refresh_labels,
    save_main_window_state,
):
    """Return the frame close handler used by the shell builder."""

    def exit_main_loop_after_destroy():
        # A destroyed HWND does not always make wxMSW's active event loop
        # return (observed in the packaged Session 1 acceptance run). The
        # frame owns the application reference, so explicitly end the loop
        # after destruction instead of leaving a headless process behind.
        enabled = bool(
            getattr(frame, "_wx_shell_exit_main_loop_on_close", False)
        )
        record_terminal_event(
            "wx-shell-exit-policy", ready=enabled
        )
        if not enabled:
            return
        app = getattr(frame, "_wx_app", None)
        exit_main_loop = getattr(app, "ExitMainLoop", None)
        if callable(exit_main_loop):
            try:
                exit_main_loop()
                record_terminal_event(
                    "wx-shell-exit-main-loop-returned", accepted=True
                )
            except Exception as exc:
                frame._wx_shell_exit_loop_error_type = type(exc).__name__
                record_terminal_event(
                    "wx-shell-exit-main-loop-error",
                    exception_type=type(exc).__name__,
                )

    def close(_event):
        frame._wx_shell_close_started = True
        record_terminal_event("wx-shell-close-enter", closed=True)
        # W55 PKGREG-SHUTDOWN-BISTABLE-NON-TERMINATION closed-owner repair:
        # the former frame.Hide() before shutdown/Destroy was observed hung
        # on the main thread (py-spy inside Hide) while the same bytes also
        # exited cleanly, i.e. a bistable teardown race. Hide() is redundant
        # (Destroy hides/removes the window) so it no longer gates shutdown.
        # Order is: page teardown -> chrome close -> lifecycle.shutdown
        # (bounded, never blocks) -> child close -> Destroy. Reentrant closes
        # are ignored via lifecycle.shutdown_started.
        if getattr(frame, "_wx_shell_destroy_scheduled", False):
            try:
                _event.Veto()
            except Exception:
                pass
            return
        if lifecycle.shutdown_started:
            pending_native = bool(
                getattr(frame, "_wx_shell_native_teardown_pending", False)
                or any(
                    getattr(win, "_wx_terminal_close_pending", False)
                    for win in chrome_windows
                )
            )
            if pending_native:
                frame._wx_shell_native_teardown_pending = True
                if not getattr(frame, "_wx_shell_destroy_scheduled", False):
                    frame._wx_shell_destroy_scheduled = True

                    def destroy_after_native_callback_window():
                        frame._wx_shell_destroy_timer = None
                        if getattr(frame, "_wx_shell_destroy_completed", False):
                            return
                        try:
                            if frame.IsBeingDeleted():
                                return
                        except (AttributeError, RuntimeError):
                            return
                        frame._wx_shell_destroy_completed = True
                        try:
                            frame._wx_shell_destroy_return = bool(frame.Destroy())
                        except Exception as exc:
                            frame._wx_shell_destroy_error_type = type(exc).__name__
                        record_terminal_event(
                            "wx-shell-destroy-requested",
                            accepted=bool(
                                getattr(frame, "_wx_shell_destroy_return", False)
                            ),
                            pending_native=True,
                        )
                        exit_main_loop_after_destroy()

                    frame._wx_shell_destroy_timer = wx.CallLater(
                        350, destroy_after_native_callback_window
                    )
                try:
                    _event.Veto()
                except Exception:
                    pass
                return
            try:
                frame.Destroy()
            except Exception:
                pass
            exit_main_loop_after_destroy()
            return
        # Persist main-window layout first (best-effort; shutdown never blocks
        # on it) so save/restart restores size/position/maximized/selected tab.
        save_main_window_state(frame, notebook)
        # Invoke every embedded page close callback before shutdown.
        pending_native_teardown = False
        for _key, controls in list(page_controls.items()):
            # For the Files splitter, local/remote/transfers are stored separately.
            candidates = []
            if "page" in controls:
                candidates.append(controls["page"])
            if "local" in controls:
                candidates.append(controls["local"])
            if "remote" in controls:
                candidates.append(controls["remote"])
            if "transfers" in controls:
                candidates.append(controls["transfers"])
            for host in candidates:
                cb = getattr(host, "_wx_host_close", None)
                if callable(cb):
                    try:
                        owner_pending = bool(cb())
                        pending_native_teardown = owner_pending or pending_native_teardown
                        if owner_pending:
                            frame._wx_shell_native_teardown_pending = True
                    except Exception:
                        # Swallowed so one bad page cannot block shutdown; this
                        # hides page-teardown faults from the leak counters - route
                        # them to the lifecycle diagnostics channel if a stress
                        # campaign needs them.
                        pass
        unsubscribe_language_change(refresh_labels)
        lifecycle.set_tray_notifier(None)
        # Close chrome windows first (Part 3 Rule 3) before lifecycle.shutdown.
        for win in list(chrome_windows):
            try:
                win.Close()
            except Exception:
                pass
            pending_native_teardown = (
                bool(getattr(win, "_wx_terminal_close_pending", False))
                or pending_native_teardown
            )
            if pending_native_teardown:
                frame._wx_shell_native_teardown_pending = True
        chrome_windows.clear()
        # Invalidate shell_ref so future handlers abort parenting.
        try:
            shell_ref[0] = None
        except Exception:
            pass
        # Bounded lifecycle teardown first so SSH/timers/threads are released
        # even if a later native window call misbehaves. shutdown() itself is
        # time-boxed per cleanup (see WxLifecycleController).
        lifecycle.shutdown()
        for child in wx.GetTopLevelWindows():
            if child is not frame and child.GetParent() is frame:
                try:
                    child.Close()
                except Exception:
                    pass
        frame._wx_shell_destroy_invoked = True
        if pending_native_teardown:
            if getattr(frame, "_wx_shell_destroy_scheduled", False):
                try:
                    _event.Veto()
                except Exception:
                    pass
                return
            frame._wx_shell_destroy_scheduled = True
            try:
                _event.Veto()
            except Exception:
                pass

            frame._wx_shell_native_teardown_pending = True

            def destroy_after_native_callback_window():
                frame._wx_shell_destroy_timer = None
                if getattr(frame, "_wx_shell_destroy_completed", False):
                    return
                try:
                    if frame.IsBeingDeleted():
                        return
                except AttributeError:
                    pass
                except RuntimeError:
                    return
                frame._wx_shell_destroy_completed = True
                try:
                    frame._wx_shell_destroy_return = bool(frame.Destroy())
                except Exception as exc:
                    frame._wx_shell_destroy_error_type = type(exc).__name__
                exit_main_loop_after_destroy()

            frame._wx_shell_destroy_timer = wx.CallLater(
                350, destroy_after_native_callback_window
            )
            return
        try:
            frame._wx_shell_destroy_return = bool(frame.Destroy())
        except Exception as exc:
            frame._wx_shell_destroy_error_type = type(exc).__name__
        record_terminal_event(
            "wx-shell-destroy-requested",
            accepted=bool(getattr(frame, "_wx_shell_destroy_return", False)),
            pending_native=pending_native_teardown,
        )
        exit_main_loop_after_destroy()

    return close



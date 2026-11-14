"""Shell close handler extracted from wx_shell_frame (W65 architecture split).

The handler is pure composition: it sequences page teardown, chrome close,
bounded lifecycle shutdown and the final Destroy. Keeping it in its own module
leaves the frame builder under the 500-line limit without changing behaviour.
"""

from __future__ import annotations

from hpc_gui.core.i18n import unsubscribe_language_change


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

    def close(_event):
        # W55 PKGREG-SHUTDOWN-BISTABLE-NON-TERMINATION closed-owner repair:
        # the former frame.Hide() before shutdown/Destroy was observed hung
        # on the main thread (py-spy inside Hide) while the same bytes also
        # exited cleanly, i.e. a bistable teardown race. Hide() is redundant
        # (Destroy hides/removes the window) so it no longer gates shutdown.
        # Order is: page teardown -> chrome close -> lifecycle.shutdown
        # (bounded, never blocks) -> child close -> Destroy. Reentrant closes
        # are ignored via lifecycle.shutdown_started.
        if lifecycle.shutdown_started:
            try:
                frame.Destroy()
            except Exception:
                pass
            return
        # Persist main-window layout first (best-effort; shutdown never blocks
        # on it) so save/restart restores size/position/maximized/selected tab.
        save_main_window_state(frame, notebook)
        # Invoke every embedded page close callback before shutdown.
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
                        cb()
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
        try:
            frame._wx_shell_destroy_return = bool(frame.Destroy())
        except Exception as exc:
            frame._wx_shell_destroy_error_type = type(exc).__name__

    return close



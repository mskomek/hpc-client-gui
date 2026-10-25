"""wx shell terminal workflows."""
from __future__ import annotations

from threading import Event
import shlex


def _schedule_terminal_mount(
    wx,
    *,
    terminal_page,
    terminal_sizer,
    session_state,
    initial_ssh,
    lifecycle,
    page_controls,
):
    """Mount a deferred terminal only while its owning shell is alive."""

    def mount_terminal():
        try:
            frame = terminal_page.GetTopLevelParent()
            if (
                lifecycle.shutdown_started
                or terminal_page.IsBeingDeleted()
                or frame is None
                or frame.IsBeingDeleted()
            ):
                return
        except Exception:
            return
        live_session = session_state.get("session") or {}
        live_ssh = live_session.get("ssh") if isinstance(live_session, dict) else None
        from hpc_gui.wx_terminal import build_terminal_panel

        real_panel = build_terminal_panel(
            terminal_page,
            ssh=live_ssh or initial_ssh,
            lifecycle=lifecycle,
        )
        terminal_sizer.Add(real_panel, 1, wx.EXPAND)
        terminal_page.Layout()
        session_state["_embedded_terminal_panel"] = real_panel
        controls = page_controls["NAV-TERMINAL"]
        terminal_controls = getattr(real_panel, "_wx_terminal_controls", {})
        controls.update(terminal_controls)
        controls.update(
            {"output": terminal_controls.get("output"), "panel": real_panel}
        )

        def close_terminal():
            callback = getattr(real_panel, "_wx_terminal_close", None)
            callback = callback or getattr(real_panel, "close", None)
            if callable(callback):
                callback()

        terminal_page._wx_host_close = close_terminal

    timer = wx.CallLater(1000, mount_terminal)
    terminal_page._wx_terminal_mount_timer = timer

    def cancel_mount():
        try:
            if timer.IsRunning():
                timer.Stop()
        except Exception:
            pass

    lifecycle.register_cleanup(cancel_mount)
    return timer


def _run_shell_in_terminal(session_state, parent, lifecycle, paths) -> None:
    session = session_state.get("session") or {}
    ssh = session.get("ssh")
    paths = [str(path) for path in paths if path]
    if not ssh or not paths:
        return
    from hpc_gui.wx_terminal import show_terminal

    def do_show():
        # re-read parent at call time and validate (Part 3 Rule 2)
        p = parent
        try:
            import wx
            if p is not None and not wx.Window.FindWindowById(p.GetId()):
                p = None
        except Exception:
            p = None
        # parent must be shell frame; if not alive, abort
        if p is None:
            return
        show_terminal(p, ssh=ssh, lifecycle=lifecycle)

    try:
        import wx

        if wx.IsMainThread():
            do_show()
        else:
            evt = Event()
            def _call():
                try:
                    do_show()
                finally:
                    evt.set()
            wx.CallAfter(_call)
            evt.wait(2)
    except Exception:
        # fallback direct
        try:
            do_show()
        except Exception:
            pass
    ssh.send_shell_text("\n".join(f"bash -- {shlex.quote(path)}" for path in paths) + "\n")

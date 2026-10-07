"""wx shell terminal workflows."""
from __future__ import annotations

from threading import Event, Thread
import shlex


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

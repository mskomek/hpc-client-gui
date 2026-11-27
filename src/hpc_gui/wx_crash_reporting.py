"""wx-owned crash notification; persistence and exception hooks stay neutral."""
from __future__ import annotations

import logging
from threading import Lock

from hpc_gui.core.crash_reporter import clear_crash_flag, read_crash_flag
from hpc_gui.core.debug_support import log_startup_snapshot
from hpc_gui.core.logging_setup import install_crash_logging, install_excepthook, setup_logging


def install_wx_crash_reporting(app):
    import wx

    previous = read_crash_flag()
    setup_logging()
    install_crash_logging()
    log = logging.getLogger("hpc_gui.crash")
    lock = Lock()
    pending = False

    def schedule(parent=None, *, snapshot=None, previous_session=False):
        nonlocal pending
        flag = snapshot if previous_session else read_crash_flag()
        if flag is None:
            return
        with lock:
            if pending:
                return
            pending = True

        def present():
            nonlocal pending
            try:
                if wx.GetApp() is not app:
                    return
                owner = parent or app.GetTopWindow()
                if owner is None or not owner or owner.IsBeingDeleted():
                    return
                from hpc_gui.wx_send_logs_view import show_send_logs

                show_send_logs(owner, crash_context=True, crash_summary=flag.get("summary", ""))
                # Never clear a newer exception that arrived during startup.
                if previous_session and read_crash_flag() == flag:
                    clear_crash_flag()
            except Exception:
                log.exception("Could not present crash diagnostics")
            finally:
                with lock:
                    pending = False

        try:
            wx.CallAfter(present)
        except Exception:
            with lock:
                pending = False
            log.exception("Could not schedule crash diagnostics")

    install_excepthook(schedule)
    log_startup_snapshot()

    def report_previous(parent):
        if previous is not None:
            schedule(parent, snapshot=previous, previous_session=True)

    return report_previous

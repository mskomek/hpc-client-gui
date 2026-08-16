from __future__ import annotations

import faulthandler
import logging
import sys
import threading
from logging.handlers import RotatingFileHandler

from hpc_gui.core.logging import log_path


_fault_file = None


def _is_paramiko_prefetch_shutdown(thread_name: str, exc_type, exc_value) -> bool:
    """Recognize paramiko's prefetch thread losing its channel on close.

    ``SFTPFile.prefetch`` queues every chunk of the file up front and the
    thread that drains that queue has no cancellation check, so cancelling a
    download (or simply closing the channel early) reliably makes it write to
    an already-closed socket.  The transfer itself is already reported and
    finalized by then, so treating this as an uncaught crash is wrong: it
    would also raise the crash flag and accuse the next launch of a crash.
    """
    if "_prefetch_thread" not in (thread_name or ""):
        return False
    if not issubclass(exc_type, OSError):
        return False
    return "closed" in str(exc_value).lower()


def install_crash_logging() -> None:
    """Capture uncaught worker errors and fatal Python crashes."""
    global _fault_file
    try:
        if _fault_file is None:
            _fault_file = open(log_path().with_name("crash.log"), "a", encoding="utf-8")
        faulthandler.enable(_fault_file, all_threads=True)
    except Exception:
        pass

    def _thread_hook(args):
        thread_name = getattr(args.thread, "name", "unknown")
        if _is_paramiko_prefetch_shutdown(thread_name, args.exc_type, args.exc_value):
            logging.getLogger("hpc_gui.crash").debug(
                "Ignoring paramiko prefetch shutdown race thread=%s: %s",
                thread_name, args.exc_value,
            )
            return
        logging.getLogger("hpc_gui.crash").error(
            "Uncaught thread exception thread=%s",
            thread_name,
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )
        try:
            from hpc_gui.core.crash_reporter import write_crash_flag

            write_crash_flag(args.exc_type, args.exc_value, args.exc_traceback)
        except Exception:
            pass

    def _unraisable_hook(args):
        logging.getLogger("hpc_gui.crash").error(
            "Unraisable exception object=%r", args.object,
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )
        try:
            from hpc_gui.core.crash_reporter import write_crash_flag

            write_crash_flag(args.exc_type, args.exc_value, args.exc_traceback)
        except Exception:
            pass

    threading.excepthook = _thread_hook
    sys.unraisablehook = _unraisable_hook


def setup_logging(level: int = logging.INFO) -> None:
    """Configure a rotating file logger.

    - Never raises (must not crash the GUI)
    - Single file: ~/.truba_slurm_gui/app.log
    """
    try:
        p = log_path()
        p.parent.mkdir(parents=True, exist_ok=True)

        root = logging.getLogger("hpc_gui")
        root.setLevel(level)

        # Avoid duplicating handlers on restart (e.g. interactive reload)
        if any(isinstance(h, RotatingFileHandler) for h in root.handlers):
            return

        fmt = logging.Formatter(
            fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        fh = RotatingFileHandler(
            p,
            maxBytes=2 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        fh.setFormatter(fmt)
        fh.setLevel(level)
        root.addHandler(fh)

        # Also capture warnings and reduce silent failures
        logging.captureWarnings(True)

    except Exception:
        # Never crash the GUI because of logging.
        pass


def install_excepthook() -> None:
    """Log uncaught exceptions to the app log and show crash dialog."""

    def _hook(exc_type, exc, tb):
        try:
            logging.getLogger("hpc_gui").exception("Uncaught exception", exc_info=(exc_type, exc, tb))
        except Exception:
            pass
        try:
            from hpc_gui.core.crash_reporter import write_crash_flag, show_crash_dialog

            write_crash_flag(exc_type, exc, tb)
            try:
                from PySide6.QtWidgets import QApplication

                app = QApplication.instance()
                if app is not None:
                    show_crash_dialog(None)
            except Exception:
                pass
        except Exception:
            pass
        try:
            sys.__excepthook__(exc_type, exc, tb)
        except Exception:
            pass

    sys.excepthook = _hook

from __future__ import annotations

"""Central logging utilities.

We keep a simple file-backed log that never crashes the GUI.
The UI "Logs" tab tails this file.
"""

import logging
from pathlib import Path

from hpc_gui.core.paths import app_log_dir


def _log_dir() -> Path:
    return app_log_dir()


def log_path() -> Path:
    return _log_dir() / "app.log"


def get_logger(name: str = "hpc_gui") -> logging.Logger:
    return logging.getLogger(name)


def append_log(line: str) -> None:
    """Backwards-compatible helper for legacy callers."""
    try:
        get_logger("hpc_gui.legacy").info(line)
    except Exception:
        # logging must never crash the GUI
        pass

"""Shared helpers for real wx GUI subprocess tests."""

from __future__ import annotations

import os
import sys


def wx_gui_subprocess_timeout(default: int) -> int:
    """Apply an explicit measured startup allowance to Linux GUI test runners."""
    if sys.platform.startswith("linux"):
        try:
            allowance = int(os.environ.get("HPC_GUI_WX_SUBPROCESS_TIMEOUT", ""))
        except ValueError:
            allowance = default
        return max(default, allowance)
    return default

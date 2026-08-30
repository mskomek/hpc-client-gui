from __future__ import annotations

"""Locate user-installed PuTTY and hand missing-tool setup to its official page."""

import platform
import shutil
import webbrowser
from pathlib import Path
from typing import Callable, Optional

from hpc_gui.core.i18n import t
from hpc_gui.core.paths import third_party_dir


PUTTY_PLINK_URL = "https://the.earth.li/~sgtatham/putty/latest/w64/plink.exe"


def _log(log: Optional[Callable[[str], None]], msg: str) -> None:
    if log:
        log(msg)


def plink_path() -> Path:
    return third_party_dir() / "putty" / "plink.exe"


def _prompt_download_plink(parent) -> bool:
    """Ask user permission before downloading plink.exe."""
    try:
        from PySide6.QtWidgets import QMessageBox
    except Exception:
        return False

    msg = t("putty.needed_msg").format(url=PUTTY_PLINK_URL)
    ret = QMessageBox.question(
        parent,
        t("putty.needed_title"),
        msg,
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
    )
    return ret == QMessageBox.StandardButton.Yes


def ensure_plink_available(*, log: Optional[Callable[[str], None]] = None, parent=None) -> bool:
    """Ensure plink.exe exists (Windows only)."""

    if platform.system().lower() != "windows":
        return False

    if shutil.which("plink"):
        return True
    dest = plink_path()
    if dest.exists():
        _log(log, "Legacy app-downloaded plink.exe is disabled; install PuTTY from its official page.")
        return False

    _log(log, t("putty.missing_log").format(url=PUTTY_PLINK_URL))

    if parent is None:
        _log(log, t("putty.parent_none_log"))
        return False

    if not _prompt_download_plink(parent):
        _log(log, t("putty.download_cancelled"))
        return False
    webbrowser.open("https://www.chiark.greenend.org.uk/~sgtatham/putty/latest.html")
    _log(log, "PuTTY official download page opened; automatic executable download is disabled.")
    return False

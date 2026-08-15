from __future__ import annotations

"""PuTTY tooling bootstrap (standalone).

Goal
----
HPC Client GUI must be able to run X11 forwarding on Windows *without* requiring the
user to install PuTTY/MobaXterm. For password-based SSH, Windows OpenSSH is not
practical from a GUI (no TTY), so we rely on **plink.exe**.

This module ensures a usable plink.exe exists under:
    ~/.truba_slurm_gui/third_party/putty/plink.exe

We download a single executable on demand (first use).
"""

import platform
from pathlib import Path
from typing import Callable, Optional

from hpc_gui.core.i18n import t
from hpc_gui.core.paths import third_party_dir
from hpc_gui.services.safe_download import download_atomic


PUTTY_PLINK_URL = "https://the.earth.li/~sgtatham/putty/latest/w64/plink.exe"


def _log(log: Optional[Callable[[str], None]], msg: str) -> None:
    if log:
        log(msg)


def plink_path() -> Path:
    return third_party_dir() / "putty" / "plink.exe"


def _download(url: str, dest: Path, log: Optional[Callable[[str], None]] = None, parent=None) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    progress = None
    try:
        if parent is not None:
            from PySide6.QtWidgets import QProgressDialog
            from PySide6.QtCore import Qt
            progress = QProgressDialog(t("putty.downloading"), t("common.cancel"), 0, 100, parent)
            progress.setWindowModality(Qt.WindowModality.ApplicationModal)
            progress.setMinimumDuration(0)
            progress.setValue(0)
        def update(downloaded: int, total: int) -> None:
            if total > 0 and progress is not None:
                progress.setValue(min(100, int(downloaded * 100 / total)))
        if not download_atomic(url, dest, cancelled=progress.wasCanceled if progress else None, progress=update):
            _log(log, t("putty.download_cancelled"))
            return False
        if progress is not None:
            progress.setValue(100)
        return True
    except Exception as e:
        _log(log, t("putty.download_error").format(err=e))
        return False
    finally:
        if progress is not None:
            progress.close()

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


def _prompt_unverified_plink(parent) -> bool:
    from PySide6.QtWidgets import QMessageBox
    ret = QMessageBox.question(parent, t("putty.verify_title"), t("putty.verify_msg"), QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    return ret == QMessageBox.StandardButton.Yes

def ensure_plink_available(*, log: Optional[Callable[[str], None]] = None, parent=None) -> bool:
    """Ensure plink.exe exists (Windows only)."""

    if platform.system().lower() != "windows":
        return False

    dest = plink_path()
    if dest.exists():
        return True

    _log(log, t("putty.missing_log").format(url=PUTTY_PLINK_URL))

    if parent is None:
        _log(log, t("putty.parent_none_log"))
        return False

    if not _prompt_download_plink(parent):
        _log(log, t("putty.download_cancelled"))
        return False

    _log(log, t("putty.downloading_log").format(url=PUTTY_PLINK_URL))
    ok = _download(PUTTY_PLINK_URL, dest, log=log, parent=parent)
    if ok and dest.exists():
        if not _prompt_unverified_plink(parent):
            dest.unlink(missing_ok=True)
            _log(log, t("putty.unverified_cancelled"))
            return False
        _log(log, t("putty.ready_log").format(path=dest))
        return True
    return False

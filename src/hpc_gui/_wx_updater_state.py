"""Shared state names and view data for the wx updater."""

from __future__ import annotations

from dataclasses import dataclass

from hpc_gui import __version__


STATE_IDLE = "IDLE"
STATE_CHECKING = "CHECKING"
STATE_UP_TO_DATE = "UP_TO_DATE"
STATE_UPDATE_AVAILABLE = "UPDATE_AVAILABLE"
STATE_DOWNLOADING = "DOWNLOADING"
STATE_DOWNLOAD_CANCELLED = "DOWNLOAD_CANCELLED"
STATE_VERIFYING = "VERIFYING"
STATE_READY_TO_INSTALL = "READY_TO_INSTALL"
STATE_INSTALLING = "INSTALLING"
STATE_RESTART_REQUIRED = "RESTART_REQUIRED"
STATE_FAILED = "FAILED"


@dataclass
class _UpdateViewState:
    current_version: str = __version__
    new_version: str = ""
    release_notes: str = ""
    whats_new: list[str] = None
    download_size: int | None = None
    mandatory: bool = False
    error_message: str = ""
    error_details: str = ""

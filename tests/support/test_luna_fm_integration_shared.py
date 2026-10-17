from __future__ import annotations

import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
import pytest
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication  # noqa: E402
from hpc_gui.config.file_manager_profile import (  # noqa: E402
    normalize_file_manager_settings,
    update_profile_file_manager_settings,
)
from hpc_gui.config.jump_host_profile import normalize_jump_host_settings  # noqa: E402
from hpc_gui.config.storage import (  # noqa: E402
    load_profiles,
    merge_profile_patch,
    upsert_profile,
)
from hpc_gui.services.directory_comparison import CompareStatus  # noqa: E402
def _base_profile(name: str) -> dict:
    return {
        "id": f"id-{name}",
        "name": name,
        "host": f"{name}.example.org",
        "port": 22,
        "username": "user",
        "save_password": False,
        "password": "",
    }
class _WidgetHarness:
    """Shared get_ftp_state/update_ftp_state patching for widget tests."""

    def __init__(self, local_dir: str | None = None) -> None:
        state_patch = mock.patch(
            "hpc_gui.ui.widgets.ftp_widget.get_ftp_state",
            return_value={
                "local_dir": local_dir or os.getcwd(),
                "active_remote": "scratch",
                "splitter_sizes": [500, 500],
            },
        )
        type_patch = mock.patch(
            "hpc_gui.ui.widgets.ftp_widget.get_ftp_transfer_type",
            return_value="auto",
        )
        update_patch = mock.patch(
            "hpc_gui.ui.widgets.ftp_widget.update_ftp_state",
            return_value={},
        )
        state_patch.start()
        type_patch.start()
        update_patch.start()
        self._patches = (state_patch, type_patch, update_patch)

    def stop(self) -> None:
        for patcher in reversed(self._patches):
            patcher.stop()
class _Entry:
    def __init__(self, name: str, *, size: int = 1):
        self.name = name
        self.path = name
        self.is_dir = False
        self.size = size
        self.mtime = int(time.time())
        self.mode = 0o644
class _FakeActivePanel:
    """Minimal active-remote-panel double for comparison orchestration."""

    def __init__(self, directory: str) -> None:
        self.current_dir = directory
        self._snapshot: tuple[str, list] = ("", [])

    def set_dir(self, target: str) -> None:
        self.current_dir = target

    def commit(self, directory: str, entries: list) -> None:
        self._snapshot = (directory, list(entries))

    def current_entries_snapshot(self):
        if self._snapshot[0] != self.current_dir:
            return "", []
        return self._snapshot

    def clear_comparison_statuses(self) -> None:
        return None

    def apply_comparison_statuses(self, statuses: dict) -> None:
        self.applied = dict(statuses)
if __name__ == "__main__":
    unittest.main()

__all__ = [
    'os',
    'sys',
    'tempfile',
    'time',
    'unittest',
    'Path',
    'SimpleNamespace',
    'mock',
    'pytest',
    'QApplication',
    'normalize_file_manager_settings',
    'update_profile_file_manager_settings',
    'normalize_jump_host_settings',
    'load_profiles',
    'merge_profile_patch',
    'upsert_profile',
    'CompareStatus',
    '_base_profile',
    '_WidgetHarness',
    '_Entry',
    '_FakeActivePanel',
]

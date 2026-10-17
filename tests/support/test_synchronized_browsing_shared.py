from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
from unittest.mock import patch
import pytest
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication  # noqa: E402
from hpc_gui.config.file_manager_profile import (  # noqa: E402
    normalize_file_manager_settings,
    patch_file_manager_settings,
)
from hpc_gui.services.synchronized_browsing import (  # noqa: E402
    SyncRoots,
    local_to_remote,
    normalize_local_root,
    normalize_remote_root,
    remote_to_local,
)
class _CountingRemotePanel:
    """Records set_dir calls without touching a real backend."""

    def __init__(self) -> None:
        self.current_dir = "/start"
        self.set_dir_calls: list[str] = []

    def set_dir(self, target: str) -> bool:
        self.set_dir_calls.append(target)
        self.current_dir = target
        return True
if __name__ == "__main__":
    unittest.main()

__all__ = [
    'os',
    'sys',
    'tempfile',
    'unittest',
    'Path',
    'SimpleNamespace',
    'mock',
    'patch',
    'pytest',
    'QApplication',
    'normalize_file_manager_settings',
    'patch_file_manager_settings',
    'SyncRoots',
    'local_to_remote',
    'normalize_local_root',
    'normalize_remote_root',
    'remote_to_local',
    '_CountingRemotePanel',
]

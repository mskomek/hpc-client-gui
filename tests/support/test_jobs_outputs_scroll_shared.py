from __future__ import annotations

import pytest
import os
import unittest
from unittest.mock import patch
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication, QMainWindow, QTextEdit
from PySide6.QtCore import QCoreApplication, QEvent, Qt
from PySide6.QtTest import QTest
from hpc_gui.ui.widgets.jobs_outputs_widget import (
    JobsOutputsWidget,
    _NavigableTextEdit,
    _OutputFollowerWidget,
)
if __name__ == "__main__":
    unittest.main()

__all__ = [
    'pytest',
    'os',
    'unittest',
    'patch',
    'QApplication',
    'QMainWindow',
    'QTextEdit',
    'QCoreApplication',
    'QEvent',
    'Qt',
    'QTest',
    'JobsOutputsWidget',
    '_NavigableTextEdit',
    '_OutputFollowerWidget',
]

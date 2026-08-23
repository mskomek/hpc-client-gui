"""Shared pytest fixtures.

The autouse fixture below neuters the two MainWindow startup side effects
(the changelog modal after 700 ms and the background update check after
1500 ms). Tests never run a Qt event loop of their own, so those single-shot
timers otherwise detonate inside the next unrelated test that pumps events,
opening modal dialogs that block the suite forever. Only these two methods
are stubbed; every other QTimer.singleShot user keeps working.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

# QtWebEngine's Chromium profile teardown segfaults at interpreter exit in
# offscreen test runs, so tests use the plain console fallback instead.
os.environ.setdefault("HPC_GUI_DISABLE_WEBENGINE", "1")

import pytest  # noqa: E402

from hpc_gui.ui import main_window as main_window_module  # noqa: E402


@pytest.fixture(autouse=True)
def _no_main_window_startup_popups():
    with (
        patch.object(
            main_window_module.MainWindow,
            "_show_changelog_dialog",
            lambda self, text: None,
        ),
        patch.object(
            main_window_module.MainWindow,
            "_check_for_updates",
            lambda self, manual=True: None,
        ),
    ):
        yield

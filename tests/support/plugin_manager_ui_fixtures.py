"""Qt fixtures for deterministic Plugin Manager GUI tests."""

from __future__ import annotations

from unittest import mock

import pytest


@pytest.fixture(scope="module", autouse=True)
def qapp():
    from PySide6.QtWidgets import QApplication
    from hpc_gui.core.i18n import load_language

    app = QApplication.instance() or QApplication([])
    load_language("en")
    yield app
    load_language("en")


@pytest.fixture()
def frozen_thread_pool():
    """Prevent queued workers from running twice in synchronous UI tests."""

    class FakePool:
        def start(self, runnable, *args, **kwargs):
            return None

    with mock.patch(
        "PySide6.QtCore.QThreadPool.globalInstance", create=True
    ) as instance:
        instance.return_value = FakePool()
        yield

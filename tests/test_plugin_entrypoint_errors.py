"""Regression tests: Plugin Manager entry-point failures must be visible."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    from hpc_gui.core.i18n import load_language

    load_language("en")
    yield app


class _Dummy:
    _logger = logging.getLogger("test.dummy")


def test_open_plugins_surfaces_failure_instead_of_silence(qapp, monkeypatch):
    from hpc_gui.ui import main_window as mw_module

    dummy = _Dummy()
    reported = []

    def boom(*args, **kwargs):
        raise RuntimeError("plugin manager exploded")

    monkeypatch.setattr(
        "hpc_gui.ui.dialogs.plugin_manager_dialog.PluginManagerDialog",
        boom,
    )
    monkeypatch.setattr(
        mw_module,
        "show_exception",
        lambda parent, **kwargs: reported.append(kwargs),
    )

    # Must not raise and must not swallow: show_exception is called with a
    # translated user message.
    mw_module.MainWindow._open_plugins(dummy)

    assert len(reported) == 1
    kwargs = reported[0]
    assert kwargs["exc"] is not None
    assert kwargs["user_message"]
    assert kwargs["title"]


def test_open_plugins_logs_exception(qapp, monkeypatch, caplog):
    from hpc_gui.ui import main_window as mw_module

    def boom(*args, **kwargs):
        raise RuntimeError("plugin manager exploded")

    monkeypatch.setattr(
        "hpc_gui.ui.dialogs.plugin_manager_dialog.PluginManagerDialog",
        boom,
    )
    monkeypatch.setattr(mw_module, "show_exception", lambda parent, **kwargs: None)

    with caplog.at_level(logging.ERROR, logger="hpc_gui.ui.main_window"):
        mw_module.MainWindow._open_plugins(_Dummy())

    assert any(
        "Opening the Plugin Manager failed" in record.getMessage()
        for record in caplog.records
    )

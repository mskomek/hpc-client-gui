from __future__ import annotations

import os
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from hpc_gui.services.transfer_conflict_policy import clear_session_conflict_action
from hpc_gui.ui.dialogs.transfer_conflict_dialog import (
    TransferConflictDecision,
    TransferConflictInfo,
    TransferConflictDialog,
)
from hpc_gui.ui.widgets.ftp_widget import TransferActivityPanel
from hpc_gui.ui.widgets.remote_dir_panel import RemoteDirPanel


@pytest.mark.gui
@pytest.mark.qt
def test_transfer_activity_events_preserve_user_selected_tab():
    app = QApplication.instance() or QApplication([])
    panel = TransferActivityPanel()
    item = SimpleNamespace(op="upload", src="local.txt", dst="/remote/local.txt")
    try:
        for index, view in enumerate(
            (panel.queue_list, panel.failed_list, panel.completed_list)
        ):
            panel.tabs.setCurrentIndex(index)
            panel.record("queued", [item], "Upload")
            assert panel.tabs.currentWidget() is view
            panel.record("failed", [item], "Upload")
            assert panel.tabs.currentWidget() is view
            panel.record("completed", [item], "Upload")
            assert panel.tabs.currentWidget() is view
        assert [panel.tabs.tabText(index) for index in range(3)] == [
            "Queue (0)",
            "Failed (1)",
            "Completed (1)",
        ]
    finally:
        panel.deleteLater()
        app.processEvents()


@pytest.mark.unit
@pytest.mark.qt
def test_conflict_always_use_is_session_scoped_and_can_be_download_only():
    app = QApplication.instance() or QApplication([])
    panel = RemoteDirPanel()
    source = TransferConflictInfo("source", size=4, mtime=3)
    target = TransferConflictInfo("target", size=4, mtime=2)
    clear_session_conflict_action()
    try:
        with patch.object(
            TransferConflictDialog,
            "get_decision",
            side_effect=[
                TransferConflictDecision(
                    "skip", always_use=True, apply_downloads_only=True
                ),
                TransferConflictDecision("overwrite"),
            ],
        ) as get_decision:
            assert panel._conflict_decision(source, target, direction="upload") == "skip"
            assert panel._conflict_decision(source, target, direction="upload") == "overwrite"
            assert panel._conflict_decision(source, target, direction="download") == "skip"
            assert get_decision.call_count == 2
    finally:
        clear_session_conflict_action()
        panel.deleteLater()
        app.processEvents()


@pytest.mark.unit
def test_overwrite_if_newer_skips_when_mtime_metadata_is_unknown():
    source = TransferConflictInfo("source", size=5, mtime=0)
    target = TransferConflictInfo("target", size=5, mtime=0)
    decision = TransferConflictDecision("overwrite_if_newer")
    assert RemoteDirPanel._normalize_conflict_decision(
        decision, source, target
    ) == "skip"

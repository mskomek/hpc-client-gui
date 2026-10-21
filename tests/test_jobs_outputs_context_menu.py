from types import SimpleNamespace
from unittest.mock import patch

from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QApplication, QMessageBox

from hpc_gui.ui.widgets.jobs_outputs_widget import JobsOutputsWidget


class _FakeSignal:
    def __init__(self) -> None:
        self.callback = None

    def connect(self, callback) -> None:
        self.callback = callback

    def emit(self) -> None:
        if self.callback is not None:
            self.callback()


class _FakeAction:
    def __init__(self) -> None:
        self.enabled = True
        self.triggered = _FakeSignal()

    def setEnabled(self, enabled: bool) -> None:
        self.enabled = enabled


class _FakeMenu:
    created = []

    def __init__(self, _parent) -> None:
        self.action = None
        type(self).created.append(self)

    def addAction(self, _label: str) -> _FakeAction:
        self.action = _FakeAction()
        return self.action

    def exec(self, _position) -> None:
        return None


def test_jobs_context_menu_is_wired_and_cancels_only_after_confirmation() -> None:
    app = QApplication.instance() or QApplication([])
    widget = JobsOutputsWidget()
    widget.session = {"slurm": object()}
    widget.jobs_text.setPlainText("17 RUNNING example\n")
    job = SimpleNamespace(job_id="17", state="RUNNING")
    _FakeMenu.created.clear()
    assert (
        widget.jobs_text.contextMenuPolicy()
        == Qt.ContextMenuPolicy.CustomContextMenu
    )

    try:
        with (
            patch(
                "hpc_gui.ui.widgets.jobs_outputs_widget.parse_squeue",
                return_value=[job],
            ),
            patch("hpc_gui.ui.widgets.jobs_outputs_widget.QMenu", _FakeMenu),
            patch(
                "hpc_gui.ui.widgets.jobs_outputs_widget.QMessageBox.question",
                return_value=QMessageBox.StandardButton.Yes,
            ),
            patch.object(widget, "cancel_job") as cancel_job,
        ):
            widget.jobs_text.customContextMenuRequested.emit(QPoint(1, 1))

            assert len(_FakeMenu.created) == 1
            action = _FakeMenu.created[0].action
            assert action is not None and action.enabled
            action.triggered.emit()

        assert widget.cancel_id.text() == "17"
        cancel_job.assert_called_once_with()
    finally:
        widget.shutdown()
        widget.deleteLater()
        app.processEvents()


def test_jobs_context_menu_disables_cancel_for_inactive_jobs() -> None:
    app = QApplication.instance() or QApplication([])
    widget = JobsOutputsWidget()
    widget.session = {"slurm": object()}
    widget.jobs_text.setPlainText("17 COMPLETED example\n")
    job = SimpleNamespace(job_id="17", state="COMPLETED")
    _FakeMenu.created.clear()

    try:
        with (
            patch(
                "hpc_gui.ui.widgets.jobs_outputs_widget.parse_squeue",
                return_value=[job],
            ),
            patch("hpc_gui.ui.widgets.jobs_outputs_widget.QMenu", _FakeMenu),
        ):
            widget.jobs_text.customContextMenuRequested.emit(QPoint(1, 1))

        assert len(_FakeMenu.created) == 1
        action = _FakeMenu.created[0].action
        assert action is not None and not action.enabled
    finally:
        widget.shutdown()
        widget.deleteLater()
        app.processEvents()

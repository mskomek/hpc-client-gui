from unittest.mock import patch

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication, QWidget

from hpc_gui.core.debug_telemetry import DebugTelemetry


def test_key_event_with_keyboard_modifiers_is_logged_without_error() -> None:
    QApplication.instance() or QApplication([])
    telemetry = DebugTelemetry()
    widget = QWidget()
    event = QKeyEvent(
        QEvent.Type.KeyPress,
        Qt.Key.Key_Delete,
        Qt.KeyboardModifier.NoModifier,
    )

    with patch.object(telemetry._log, "info") as log_info:
        assert telemetry.eventFilter(widget, event) is False

    log_info.assert_called_once()
    assert log_info.call_args.args[-1] == Qt.KeyboardModifier.NoModifier.value

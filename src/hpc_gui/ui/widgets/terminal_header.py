from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QToolButton, QWidget

from hpc_gui.core.i18n import t


class TerminalHeader(QWidget):
    """Presentation-only terminal status and local actions."""

    find_requested = Signal()
    clear_requested = Signal()
    font_delta_requested = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.status_label = QLabel()
        self.status_label.setFrameShape(QFrame.Shape.NoFrame)
        self.status_label.setMargin(0)
        self.status_label.setWordWrap(False)
        self.identity_label = QLabel()
        identity_font = self.identity_label.font()
        identity_font.setBold(True)
        self.identity_label.setFont(identity_font)
        self.separator_label = QLabel("•")
        self.dimensions_label = QLabel("—")
        self.find_button = QToolButton()
        self.clear_button = QToolButton()
        self.font_down_button = QToolButton()
        self.font_up_button = QToolButton()
        for button in (
            self.find_button,
            self.clear_button,
            self.font_down_button,
            self.font_up_button,
        ):
            button.setAutoRaise(True)
        self.find_button.clicked.connect(self.find_requested)
        self.clear_button.clicked.connect(self.clear_requested)
        self.font_down_button.clicked.connect(lambda: self.font_delta_requested.emit(-1))
        self.font_up_button.clicked.connect(lambda: self.font_delta_requested.emit(1))
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(self.status_label)
        layout.addWidget(self.separator_label)
        layout.addWidget(self.identity_label)
        layout.addStretch(1)
        layout.addWidget(self.find_button)
        layout.addWidget(self.font_down_button)
        layout.addWidget(self.font_up_button)
        layout.addWidget(self.clear_button)
        layout.addWidget(self.dimensions_label)
        self.retranslate_ui()

    def set_status(self, text: str) -> None:
        self.status_label.setText(text)

    def set_identity(self, text: str) -> None:
        self.identity_label.setText(text)

    def set_dimensions(self, columns: int, rows: int) -> None:
        self.dimensions_label.setText(f"{columns}×{rows}")

    def retranslate_ui(self) -> None:
        self.status_label.setText(t("login.status_disconnected"))
        self.identity_label.setText(t("login.terminal_protocol_ssh"))
        self.find_button.setText(t("login.terminal_find"))
        self.find_button.setToolTip(t("login.terminal_find"))
        self.clear_button.setText(t("login.terminal_clear_short"))
        self.clear_button.setToolTip(t("login.terminal_clear"))
        self.font_down_button.setText(t("login.terminal_font_decrease_short"))
        self.font_down_button.setToolTip(t("login.terminal_font_decrease"))
        self.font_up_button.setText(t("login.terminal_font_increase_short"))
        self.font_up_button.setToolTip(t("login.terminal_font_increase"))

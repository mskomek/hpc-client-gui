from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
from PySide6.QtWidgets import QDialog, QLabel, QProgressBar, QSplashScreen, QVBoxLayout


class StartupSplash(QSplashScreen):
    """Simple splash shown while the main window is being built."""

    WIDTH = 480
    HEIGHT = 220

    def __init__(self) -> None:
        super().__init__(self._build_pixmap())
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self._status = "Starting application..."

    @classmethod
    def _build_pixmap(cls) -> QPixmap:
        pixmap = QPixmap(cls.WIDTH, cls.HEIGHT)
        painter = QPainter(pixmap)
        painter.fillRect(pixmap.rect(), QColor("#f7f8fa"))

        painter.setPen(QColor("#1f2937"))
        title_font = QFont("Segoe UI", 23, QFont.Weight.DemiBold)
        painter.setFont(title_font)
        painter.drawText(0, 56, cls.WIDTH, 38, Qt.AlignmentFlag.AlignHCenter, "HPC WORKSPACE")

        subtitle_font = QFont("Segoe UI", 10)
        painter.setFont(subtitle_font)
        painter.setPen(QColor("#5b6472"))
        painter.drawText(0, 108, cls.WIDTH, 24, Qt.AlignmentFlag.AlignHCenter, "SSH  •  Slurm  •  X11 Workflow Manager")
        painter.end()
        return pixmap

    def set_status(self, message: str) -> None:
        self._status = message
        self.showMessage(
            message,
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom,
            QColor("#6b7280"),
        )


class UpdateSplash(QDialog):
    """Splash-sized progress window used while an application update runs."""

    WIDTH = StartupSplash.WIDTH
    HEIGHT = StartupSplash.HEIGHT

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("HPC WORKSPACE")
        self.setFixedSize(self.WIDTH, self.HEIGHT)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setStyleSheet(
            "QDialog { background: #f7f8fa; }"
            "QLabel#title { color: #1f2937; font: 600 23px 'Segoe UI'; }"
            "QLabel#subtitle { color: #5b6472; font: 10pt 'Segoe UI'; }"
            "QLabel#status { color: #6b7280; font: 10pt 'Segoe UI'; }"
            "QProgressBar { height: 8px; border: 0; background: #e5e7eb; }"
            "QProgressBar::chunk { background: #2563eb; }"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 26)
        layout.setSpacing(10)
        title = QLabel("HPC WORKSPACE", self)
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(title)
        subtitle = QLabel("SSH  •  Slurm  •  X11 Workflow Manager", self)
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(subtitle)
        layout.addStretch(1)
        self.status_label = QLabel(self)
        self.status_label.setObjectName("status")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.status_label)
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setTextVisible(False)
        layout.addWidget(self.progress_bar)

    def set_status(self, message: str, value: int) -> None:
        self.status_label.setText(message)
        self.progress_bar.setValue(max(0, min(100, int(value))))

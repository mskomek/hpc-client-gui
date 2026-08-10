from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
from PySide6.QtWidgets import QSplashScreen


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

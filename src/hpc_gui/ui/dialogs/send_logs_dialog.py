from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit,
    QLabel, QMessageBox, QFileDialog,
)

from hpc_gui.core.i18n import t
from hpc_gui.core.logging import log_path
from hpc_gui.core.diagnostics import create_diagnostic_bundle
from hpc_gui.core.log_redaction import redact_text


class SendLogsDialog(QDialog):

    def __init__(self, parent=None, *, crash_context: bool = False, crash_summary: str = ""):
        super().__init__(parent)
        self._crash_context = crash_context
        self._crash_summary = crash_summary
        self.setWindowTitle(
            t("crash.dialog_title_crash") if crash_context else t("crash.dialog_title")
        )
        self.setMinimumSize(700, 500)
        self.resize(820, 620)
        self.setWindowModality(Qt.WindowModality.WindowModal)

        self._header_lbl = QLabel(self)
        self._header_lbl.setWordWrap(True)
        if crash_context:
            ctx = t("crash.crash_context")
            if crash_summary:
                ctx += "\n\n" + crash_summary[:1000]
            self._header_lbl.setText(ctx)
            self._header_lbl.setStyleSheet("QLabel { color: #b00020; font-weight: 600; padding: 8px; }")
        else:
            self._header_lbl.setText(t("crash.manual_context"))
            self._header_lbl.setStyleSheet("QLabel { padding: 8px; }")

        self._log_view = QTextEdit(self)
        self._log_view.setReadOnly(True)
        self._log_view.setStyleSheet("QTextEdit { font-family: 'Consolas', 'Courier New', monospace; font-size: 12px; }")

        self._btn_copy = QPushButton(t("crash.copy_logs"), self)
        self._btn_copy.clicked.connect(self._copy_to_clipboard)

        self._btn_export = QPushButton(t("crash.export_diagnostics"), self)
        self._btn_export.clicked.connect(self._export_diagnostics)

        self._btn_close = QPushButton(t("crash.close"), self)
        self._btn_close.clicked.connect(self.accept)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn_row.addWidget(self._btn_copy)
        btn_row.addWidget(self._btn_export)
        btn_row.addWidget(self._btn_close)

        layout = QVBoxLayout(self)
        layout.addWidget(self._header_lbl)
        layout.addWidget(self._log_view, 1)
        layout.addLayout(btn_row)

        self._load_logs()

    def retranslate_ui(self) -> None:
        self.setWindowTitle(
            t("crash.dialog_title_crash") if self._crash_context else t("crash.dialog_title")
        )
        if self._crash_context:
            ctx = t("crash.crash_context")
            if self._crash_summary:
                ctx += "\n\n" + self._crash_summary[:1000]
            self._header_lbl.setText(ctx)
        else:
            self._header_lbl.setText(t("crash.manual_context"))
        self._btn_copy.setText(t("crash.copy_logs"))
        self._btn_export.setText(t("crash.export_diagnostics"))
        self._btn_close.setText(t("crash.close"))

    def _load_logs(self) -> None:
        p = log_path()
        if not p.exists():
            self._log_view.setPlainText(t("logs.not_created").format(path=str(p)))
            return
        try:
            with p.open("r", encoding="utf-8", errors="replace") as fh:
                lines = fh.readlines()
            if len(lines) > 5000:
                lines = lines[-5000:]
            lines.reverse()
            self._log_view.setPlainText(redact_text("".join(lines)))
        except Exception as e:
            self._log_view.setPlainText(t("logs.read_failed").format(err=str(e)))

    def _copy_to_clipboard(self) -> None:
        QGuiApplication.clipboard().setText(self._log_view.toPlainText())

    def _export_diagnostics(self) -> None:
        target_dir = QFileDialog.getExistingDirectory(self, t("logs.select_output_folder"))
        if not target_dir:
            return
        try:
            p = create_diagnostic_bundle(target_dir)
            QMessageBox.information(self, t("logs.diagnostics_title"), t("logs.bundle_created").format(path=p))
        except Exception as e:
            QMessageBox.critical(self, t("logs.diagnostics_title"), t("logs.bundle_failed").format(err=e))

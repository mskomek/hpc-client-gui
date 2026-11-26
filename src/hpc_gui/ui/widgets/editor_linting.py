"""Editor linting mixin behavior."""

from __future__ import annotations

from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QVBoxLayout, QMessageBox
)

from hpc_gui.core.i18n import t




from hpc_gui.services.editor_lint import EditorLintPipeline


class EditorLintingMixin(EditorLintPipeline):
    def run_lint_for_plugin(self, plugin_id: str | None = None):
        """Scoped lint â€“ reuses the same pipeline filtered to one plugin if possible."""
        path = self.path_in.text().strip()
        text = self.text.toPlainText()
        if not path:
            QMessageBox.information(self, t("common.info"), t("editor.lint_need_path"))
            return
        issues, diagnostics = self.collect(path, text, plugin_id=plugin_id)
        if not issues and not diagnostics:
            QMessageBox.information(self, t("common.info"), t("editor.lint_ok"))
            return
        self._show_lint_results(path, issues, diagnostics)
    def run_lint(self):
        path = self.path_in.text().strip()
        text = self.text.toPlainText()
        if not path:
            QMessageBox.information(self, t("common.info"), t("editor.lint_need_path"))
            return
        issues, diagnostics = self.collect(path, text)
        if not issues and not diagnostics:
            QMessageBox.information(self, t("common.info"), t("editor.lint_ok"))
            return
        self._show_lint_results(path, issues, diagnostics)
    def _show_lint_results(self, path: str, issues: list[str], diagnostics: list) -> None:
        """Show a diagnostics dialog; double-click navigates the editor line."""
        from PySide6.QtWidgets import QDialog, QListWidget, QListWidgetItem

        labels, positions = self._lint_result_entries(issues, diagnostics)

        dialog = QDialog(self)
        dialog.setWindowTitle(
            t("editor.lint_results_title")
        )
        dialog.resize(640, 380)
        layout = QVBoxLayout(dialog)
        listing = QListWidget(dialog)
        layout.addWidget(listing)

        for label in labels:
            listing.addItem(QListWidgetItem(label))

        def navigate(item_index: int) -> None:
            line = positions[item_index] if item_index < len(positions) else -1
            if line < 0:
                return
            cursor = self.text.textCursor()
            block = self.text.document().findBlockByLineNumber(line)
            cursor.setPosition(block.position())
            cursor.movePosition(QTextCursor.MoveOperation.EndOfLine, QTextCursor.MoveMode.KeepAnchor)
            self.text.setTextCursor(cursor)
            self.text.setFocus()

        def on_activated(index) -> None:
            navigate(index.row())

        listing.itemDoubleClicked.connect(lambda _item: navigate(listing.currentRow()))
        listing.itemActivated.connect(on_activated)
        dialog.exec()

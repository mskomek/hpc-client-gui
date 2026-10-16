"""Editor document actions mixin behavior."""

from __future__ import annotations

import posixpath

from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QTextEdit, QMessageBox
)

from hpc_gui.core.i18n import t
from hpc_gui.services.editor_controller import EditorCommandService
from hpc_gui.ui.dialogs.slurm_array_dialog import edit_slurm_array
from hpc_gui.ui.widgets.editor_document_view import _EditorDocument




class EditorDocumentActionsMixin:
    def new_document(self) -> None:
        self._add_document()
    def execute_active(self) -> None:
        path = self.path_in.text().strip()
        mode = EditorCommandService.execute_mode(path)
        if mode == "submit":
            self.save_path(force_submit=True)
        elif mode == "run":
            self.save_path(run_in_terminal=True)
        else:
            self.save_path()
    @property
    def text(self) -> QTextEdit:
        document = self._current_document()
        if document is None:
            document = self._add_document()
        return document.text
    def _current_document(self) -> _EditorDocument | None:
        current = self.document_tabs.currentWidget()
        return current if isinstance(current, _EditorDocument) else None
    @staticmethod
    def _tab_title(path: str) -> str:
        return posixpath.basename(path.rstrip("/")) if path else t("editor.title")
    def _add_document(
        self, path: str = "", content: str = "", is_local: bool = False
    ) -> _EditorDocument:
        document = _EditorDocument(
            self, path, content, self.document_tabs, is_local=is_local
        )
        index = self.document_tabs.addTab(document, self._tab_title(path))
        self.document_tabs.setTabToolTip(index, path)
        self.document_tabs.setCurrentIndex(index)
        return document
    def _document_index_for_path(self, path: str) -> int:
        for index in range(self.document_tabs.count()):
            document = self.document_tabs.widget(index)
            if isinstance(document, _EditorDocument) and document.path == path:
                return index
        return -1
    def _on_current_document_changed(self, _index: int) -> None:
        document = self._current_document()
        path = document.path if document is not None else ""
        self.current_path = path or None
        self.path_in.setText(path)
        self._update_save_actions(path)
    def _close_document_tab(self, index: int) -> None:
        document = self.document_tabs.widget(index)
        if isinstance(document, _EditorDocument) and self._is_document_modified(document):
            box = QMessageBox(self)
            box.setWindowTitle(t("common.confirm"))
            box.setText(t("common.unsaved_changes"))
            save = box.addButton(t("common.save_changes"), QMessageBox.ButtonRole.AcceptRole)
            discard = box.addButton(t("common.dont_save"), QMessageBox.ButtonRole.DestructiveRole)
            box.addButton(t("common.cancel"), QMessageBox.ButtonRole.RejectRole)
            box.exec()
            if box.clickedButton() is save:
                self.document_tabs.setCurrentIndex(index)
                self.save_path()
                if self._is_document_modified(document):
                    return
            elif box.clickedButton() is not discard:
                return
        self.document_tabs.removeTab(index)
        if document is not None:
            document.deleteLater()
        if self.document_tabs.count() == 0:
            self._add_document()
    def close_active_tab(self) -> None:
        index = self.document_tabs.currentIndex()
        if index >= 0:
            self._close_document_tab(index)
    def switch_document(self, offset: int) -> None:
        count = self.document_tabs.count()
        if count < 2:
            return
        index = (self.document_tabs.currentIndex() + offset) % count
        self.document_tabs.setCurrentIndex(index)
    def focus_open_path(self) -> None:
        self.path_in.setFocus()
        self.path_in.selectAll()
    def find_text(self) -> None:
        self.find_bar.setVisible(True)
        if self._last_find_query and not self.find_in.text():
            self.find_in.setText(self._last_find_query)
        self.find_in.setFocus(Qt.FocusReason.ShortcutFocusReason)
        self.find_in.selectAll()
    def find_next(self) -> None:
        query = self.find_in.text()
        if not query:
            self.find_text()
            return
        self._last_find_query = query
        if self.text.find(query):
            return
        cursor = self.text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        self.text.setTextCursor(cursor)
        self.text.find(query)
    def replace_current(self) -> bool:
        query = self.find_in.text()
        if not query:
            self.find_text()
            return False
        cursor = self.text.textCursor()
        if cursor.selectedText() != query:
            self.find_next()
            cursor = self.text.textCursor()
            if cursor.selectedText() != query:
                return False
        cursor.insertText(self.replace_in.text())
        self.text.setTextCursor(cursor)
        return True
    def replace_all(self) -> int:
        query = self.find_in.text()
        if not query:
            self.find_text()
            return 0
        replacement = self.replace_in.text()
        text = self.text.toPlainText()
        count = text.count(query)
        if count <= 0:
            return 0
        self.text.setPlainText(text.replace(query, replacement))
        cursor = self.text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        self.text.setTextCursor(cursor)
        return count
    def _set_active_document_path(self, path: str) -> None:
        document = self._current_document()
        if document is None:
            document = self._add_document()
        document.path = path
        index = self.document_tabs.indexOf(document)
        self.document_tabs.setTabText(index, self._tab_title(path))
        self.document_tabs.setTabToolTip(index, path)
        self.current_path = path or None
        self.path_in.setText(path)
        self._update_save_actions(path)
    @staticmethod
    def _is_document_modified(document: _EditorDocument) -> bool:
        return document.text.toPlainText() != document.saved_text
    def _document_modified(self, document: _EditorDocument) -> None:
        index = self.document_tabs.indexOf(document)
        if index < 0:
            return
        title = self._tab_title(document.path)
        self.document_tabs.setTabText(index, f"{title} *" if self._is_document_modified(document) else title)
    def _update_save_actions(self, path: str) -> None:
        lower = path.lower()
        self.btn_save_run.setVisible(lower.endswith(".sh"))
        self.btn_save_submit.setVisible(lower.endswith((".slurm", ".sbatch")))
        self.btn_array.setVisible(lower.endswith((".slurm", ".sbatch")))
    def edit_array(self) -> None:
        edited = edit_slurm_array(self, self.text.toPlainText())
        if edited is not None:
            self.text.setPlainText(edited)

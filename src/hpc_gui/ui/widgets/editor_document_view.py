"""Document widgets used by the editor and its document behavior mixin."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QVBoxLayout, QTextEdit, QWidget

if TYPE_CHECKING:
    from hpc_gui.ui.widgets.editor_widget import EditorWidget

class _EditorTextEdit(QTextEdit):
    def __init__(self, owner: "EditorWidget", parent=None):
        super().__init__(parent)
        self._owner = owner

    def event(self, event) -> bool:  # type: ignore[override]
        if (
            event.type() == QEvent.Type.ShortcutOverride
            and (
                (
                    event.modifiers() & Qt.KeyboardModifier.ControlModifier
                    and event.key()
                    in (
                        Qt.Key.Key_S,
                        Qt.Key.Key_F,
                        Qt.Key.Key_O,
                        Qt.Key.Key_W,
                        Qt.Key.Key_Tab,
                    )
                )
                or event.key() == Qt.Key.Key_F3
            )
        ):
            event.accept()
            return True
        return super().event(event)

    def keyPressEvent(self, event) -> None:  # type: ignore[override]
        modifiers = event.modifiers()
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            if event.key() == Qt.Key.Key_S:
                if modifiers & Qt.KeyboardModifier.ShiftModifier:
                    self._owner.save_path(force_submit=True)
                else:
                    self._owner.save_path()
                event.accept()
                return
            if event.key() == Qt.Key.Key_F:
                self._owner.find_text()
                event.accept()
                return
            if event.key() == Qt.Key.Key_O:
                self._owner.focus_open_path()
                event.accept()
                return
            if event.key() == Qt.Key.Key_W:
                self._owner.close_active_tab()
                event.accept()
                return
            if event.key() == Qt.Key.Key_Tab:
                self._owner.switch_document(
                    -1
                    if modifiers & Qt.KeyboardModifier.ShiftModifier
                    else 1
                )
                event.accept()
                return
        if event.key() == Qt.Key.Key_F3:
            self._owner.find_next()
            event.accept()
            return
        if (
            event.key() == Qt.Key.Key_End
            and event.modifiers() in (
                Qt.KeyboardModifier.NoModifier,
                Qt.KeyboardModifier.ControlModifier,
            )
        ):
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.setTextCursor(cursor)
            self.ensureCursorVisible()
            scrollbar = self.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
            event.accept()
            return
        super().keyPressEvent(event)

class _EditorDocument(QWidget):
    def __init__(
        self,
        owner: "EditorWidget",
        path: str = "",
        content: str = "",
        parent=None,
        is_local: bool = False,
    ):
        super().__init__(parent)
        self.path = path
        self.is_local = is_local
        self.saved_text = content
        self.text = _EditorTextEdit(owner, self)
        self.text.setPlainText(content)
        self.text.textChanged.connect(
            lambda document=self: owner._document_modified(document)
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.text)

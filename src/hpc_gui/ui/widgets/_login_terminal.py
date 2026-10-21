"""Login terminal console helpers (Wave M01).

Qt ownership of the login widget's terminal console: the fallback console
widget, terminal key-sequence mapping, clipboard paste, shell geometry and
console log rendering. Functions take the owning widget explicitly so the
facade (``login_widget.py``) stays thin; Qt signals remain defined there.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import shiboken6
from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QApplication, QPlainTextEdit

from hpc_gui.core.logging import append_log

if TYPE_CHECKING:  # pragma: no cover - typing only, no runtime cycle
    from hpc_gui.ui.widgets.login_widget import LoginWidget


class TerminalConsole(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._key_handler = None
        self._paste_handler = None

    def set_key_handler(self, handler) -> None:
        self._key_handler = handler

    def set_paste_handler(self, handler) -> None:
        self._paste_handler = handler

    def keyPressEvent(self, event) -> None:  # type: ignore[override]
        handler = self._key_handler
        if handler is not None and handler(event):
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.RightButton:
            handler = self._paste_handler
            if handler is not None and handler():
                event.accept()
                return
        super().mousePressEvent(event)


def terminal_key_sequence(event) -> str | None:
    key = event.key()
    mods = event.modifiers()
    text = event.text() or ""

    if mods & Qt.KeyboardModifier.ControlModifier and text:
        ch = text.upper()[0]
        if "@" <= ch <= "_":
            return chr(ord(ch) - 64)

    special_map = {
        Qt.Key.Key_Return: "\r",
        Qt.Key.Key_Enter: "\r",
        Qt.Key.Key_Tab: "\t",
        Qt.Key.Key_Backtab: "\x1b[Z",
        Qt.Key.Key_Backspace: "\x7f",
        Qt.Key.Key_Escape: "\x1b",
        Qt.Key.Key_Left: "\x1b[D",
        Qt.Key.Key_Right: "\x1b[C",
        Qt.Key.Key_Up: "\x1b[A",
        Qt.Key.Key_Down: "\x1b[B",
        Qt.Key.Key_Home: "\x1b[H",
        Qt.Key.Key_End: "\x1b[F",
        Qt.Key.Key_Delete: "\x1b[3~",
        Qt.Key.Key_PageUp: "\x1b[5~",
        Qt.Key.Key_PageDown: "\x1b[6~",
        Qt.Key.Key_Insert: "\x1b[2~",
    }
    if key in special_map:
        return special_map[key]

    if len(text) == 1 and not (mods & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.MetaModifier)):
        return text

    return None


def forward_console_key_event(widget: LoginWidget, event) -> bool:
    try:
        ssh = widget._session.get("ssh") if hasattr(widget, "_session") else None
        if not ssh:
            return False
        seq = terminal_key_sequence(event)
        if not seq:
            return False
        if hasattr(ssh, "send_shell_input") and ssh.send_shell_input(seq):
            event.accept()
            return True
    except Exception:
        pass
    return False


def paste_console_clipboard(widget: LoginWidget) -> bool:
    try:
        ssh = widget._session.get("ssh") if hasattr(widget, "_session") else None
        if not ssh or not hasattr(ssh, "send_shell_input"):
            return False
        text = QApplication.clipboard().text()
        if not text:
            return False
        text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\r")
        if ssh.send_shell_input(text):
            if widget.terminal_widget is not None:
                widget.terminal_widget.focus_terminal()
            else:
                widget.console.setFocus()
            return True
    except Exception:
        pass
    return False


def console_shell_geometry(widget: LoginWidget) -> tuple[int, int]:
    try:
        viewport = widget.console.viewport()
        size = viewport.size()
        fm = widget.console.fontMetrics()
        char_width = max(1, fm.horizontalAdvance("M"))
        line_height = max(1, fm.lineSpacing())
        width = size.width()
        height = size.height()
        if width < char_width * 4 or height < line_height * 2:
            return (120, 40)
        cols = max(20, width // char_width)
        rows = max(5, height // line_height)
        return (cols, rows)
    except Exception:
        return (120, 40)


def sync_shell_geometry(widget: LoginWidget) -> None:
    try:
        ssh = widget._session.get("ssh") if hasattr(widget, "_session") else None
        if not ssh or not hasattr(ssh, "resize_shell_pty"):
            return
        cols, rows = console_shell_geometry(widget)
        if widget._last_shell_geometry == (cols, rows):
            return
        ssh.resize_shell_pty(cols, rows)
        widget._last_shell_geometry = (cols, rows)
        widget.terminal_dimensions_label.setText(f"{cols}×{rows}")
    except Exception:
        pass


def schedule_console_render(widget: LoginWidget) -> None:
    if not widget._console_render_timer.isActive():
        widget._console_render_timer.start()


def render_console_view(widget: LoginWidget) -> None:
    try:
        lines = list(widget._console_log_lines)
        text = "\n".join(lines)
        widget.console.blockSignals(True)
        try:
            widget.console.setPlainText(text)
            cursor = widget.console.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            widget.console.setTextCursor(cursor)
            widget.console.ensureCursorVisible()
        finally:
            widget.console.blockSignals(False)
    except Exception:
        pass


def append_log_line(widget: LoginWidget, msg: str) -> None:
    text = (msg or "").rstrip("\n")
    widget._console_log_lines.extend(text.splitlines() or [""])
    if len(widget._console_log_lines) > 2000:
        del widget._console_log_lines[:-2000]
    schedule_console_render(widget)


def append_console_to_widget(widget: LoginWidget, msg: str) -> None:
    # Guard against "Internal C++ object already deleted" during shutdown.
    try:
        if hasattr(widget, "console") and shiboken6.isValid(widget.console):
            append_log_line(widget, msg)
    except RuntimeError:
        pass
    append_log(msg)


def append_ssh_console_to_widget(widget: LoginWidget, msg: str) -> None:
    try:
        if hasattr(widget, "console") and shiboken6.isValid(widget.console):
            append_log_line(widget, msg)
    except RuntimeError:
        pass


def append_shell_output_to_widget(widget: LoginWidget, msg: str) -> None:
    try:
        if widget.terminal_widget is not None:
            return
        if not hasattr(widget, "console") or not shiboken6.isValid(widget.console):
            return
        append_log_line(widget, msg)
        schedule_console_render(widget)
    except Exception:
        pass


def handle_console_viewport_event(widget: LoginWidget, obj, event) -> bool:
    """Sync PTY geometry on console viewport resize/show. Returns False so
    the event keeps propagating to the base handler."""
    try:
        if obj is getattr(widget.console, "viewport", lambda: None)():
            if event.type() in (QEvent.Type.Resize, QEvent.Type.Show):
                sync_shell_geometry(widget)
    except Exception:
        pass
    return False


def find_terminal_text(widget: LoginWidget) -> None:
    if widget.terminal_widget is None:
        return
    from PySide6.QtWidgets import QInputDialog

    from hpc_gui.core.i18n import t

    text, ok = QInputDialog.getText(widget, t("login.terminal_find"), t("login.terminal_find"))
    if ok:
        widget.terminal_widget.find_text(text)

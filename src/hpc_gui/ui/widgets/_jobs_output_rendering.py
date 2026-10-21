"""Qt rendering helpers shared by the Jobs outputs and follower views."""

from PySide6.QtCore import QTimer
from PySide6.QtGui import QFontDatabase, QTextCursor
from PySide6.QtWidgets import QTextEdit
from shiboken6 import isValid

from ._jobs_output_text import _OUTPUT_MAX_LINES, _bounded_output_text


def _apply_terminal_output_style(widget: QTextEdit) -> None:
    widget.setLineWrapMode(QTextEdit.NoWrap)
    widget.setFont(QFontDatabase.systemFont(QFontDatabase.FixedFont))
    widget.document().setMaximumBlockCount(_OUTPUT_MAX_LINES + 1)
    widget.setStyleSheet(
        "QTextEdit { background-color: #111111; color: #e8e8e8; "
        "border: 1px solid #555; selection-background-color: #264f78; }"
        "QScrollBar:vertical { background: #ffffff; width: 12px; margin: 0; }"
        "QScrollBar:horizontal { background: #ffffff; height: 12px; margin: 0; }"
        "QScrollBar::handle:vertical, QScrollBar::handle:horizontal "
        "{ background: #bdbdbd; min-height: 20px; min-width: 20px; }"
        "QScrollBar::add-line, QScrollBar::sub-line { background: #ffffff; }"
        "QScrollBar::add-page, QScrollBar::sub-page { background: #ffffff; }"
    )


def _scroll_to_latest(
    widget: QTextEdit,
    horizontal_position: int | None = None,
) -> None:
    if not isValid(widget):
        return
    if horizontal_position is None:
        horizontal_position = widget.horizontalScrollBar().value()
    cursor = widget.textCursor()
    cursor.movePosition(QTextCursor.MoveOperation.End)
    widget.setTextCursor(cursor)
    widget.ensureCursorVisible()

    def finish_scroll() -> None:
        if not isValid(widget):
            return
        scrollbar = widget.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        horizontal_scrollbar = widget.horizontalScrollBar()
        horizontal_scrollbar.setValue(
            min(horizontal_position, horizontal_scrollbar.maximum())
        )

    finish_scroll()
    QTimer.singleShot(0, finish_scroll)


def _is_scrolled_to_bottom(widget: QTextEdit) -> bool:
    if not isValid(widget):
        return False
    scrollbar = widget.verticalScrollBar()
    return scrollbar.maximum() - scrollbar.value() <= 1


def _set_live_text(
    widget: QTextEdit,
    text: str,
    *,
    follow_latest: bool,
) -> None:
    if not isValid(widget):
        return
    scrollbar = widget.verticalScrollBar()
    horizontal_scrollbar = widget.horizontalScrollBar()
    previous_position = scrollbar.value()
    previous_horizontal_position = horizontal_scrollbar.value()
    widget.document().setMaximumBlockCount(_OUTPUT_MAX_LINES + 1)
    widget.setPlainText(_bounded_output_text(text))
    if follow_latest:
        _scroll_to_latest(
            widget,
            horizontal_position=previous_horizontal_position,
        )
    else:
        scrollbar.setValue(min(previous_position, scrollbar.maximum()))
        horizontal_scrollbar.setValue(
            min(previous_horizontal_position, horizontal_scrollbar.maximum())
        )

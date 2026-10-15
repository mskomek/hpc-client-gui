"""Consistent icons and row contrast for local and remote directory lists."""

from __future__ import annotations

from pathlib import PurePath

from PySide6.QtCore import QEvent, QObject, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import (
    QColor,
    QFont,
    QIcon,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QApplication,
    QStyleOptionViewItem,
    QStyledItemDelegate,
    QTreeWidget,
    QWidget,
)


_ROW_STYLE = """
QTreeWidget {
    background: #ffffff;
    alternate-background-color: #f2f7fd;
    selection-background-color: #cfe4fa;
    selection-color: #182b40;
}
QTreeWidget::item {
    min-height: 21px;
    padding: 2px 5px;
    border-bottom: 1px solid #f0f4f8;
}
QTreeWidget::item:selected {
    background: #cfe4fa;
    color: #182b40;
}
"""

_EXTENSION_GROUPS = (
    ({"pdf"}, "PDF", "#d64a4a"),
    ({"doc", "docx", "odt", "rtf"}, "DOC", "#3577c8"),
    ({"xls", "xlsx", "csv", "tsv", "ods"}, "XLS", "#2f9a69"),
    ({"ppt", "pptx", "odp"}, "PPT", "#d47b36"),
    (
        {"png", "jpg", "jpeg", "gif", "bmp", "svg", "webp", "tif", "tiff"},
        "IMG",
        "#8b62c8",
    ),
    ({"zip", "tar", "gz", "bz2", "xz", "7z", "rar", "tgz"}, "ZIP", "#bc842d"),
    (
        {
            "py", "js", "ts", "tsx", "jsx", "html", "css", "json", "xml",
            "yaml", "yml", "sh", "ps1", "c", "cpp", "h", "java", "go",
            "rs", "ipynb",
        },
        "<>",
        "#7359bd",
    ),
    ({"mp4", "mkv", "mov", "avi", "webm"}, "▶", "#ce5d78"),
    ({"mp3", "wav", "flac", "ogg", "m4a"}, "♪", "#368b9b"),
    ({"txt", "md", "log", "ini", "cfg", "conf", "out", "err"}, "TXT", "#617c9b"),
)
_EXTENSION_LOOKUP = {
    extension: (label, color)
    for extensions, label, color in _EXTENSION_GROUPS
    for extension in extensions
}
_ICON_CACHE: dict[tuple[str, str], QIcon] = {}


def _draw_icon(kind: str, label: str, color: str) -> QIcon:
    pixmap = QPixmap(36, 36)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    accent = QColor(color)

    if kind == "folder":
        path = QPainterPath()
        path.moveTo(4, 10)
        path.lineTo(15, 10)
        path.lineTo(18, 13)
        path.lineTo(32, 13)
        path.quadTo(34, 13, 34, 16)
        path.lineTo(31, 29)
        path.quadTo(31, 32, 28, 32)
        path.lineTo(6, 32)
        path.quadTo(3, 32, 3, 29)
        path.lineTo(3, 13)
        path.quadTo(3, 10, 4, 10)
        painter.setPen(QPen(QColor("#c58b21"), 1.3))
        painter.setBrush(QColor("#f7c957"))
        painter.drawPath(path)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#ffdc79"))
        painter.drawRoundedRect(QRectF(4, 16, 28, 13), 2, 2)
    else:
        page = QPainterPath()
        page.moveTo(9, 3)
        page.lineTo(23, 3)
        page.lineTo(30, 10)
        page.lineTo(30, 31)
        page.quadTo(30, 33, 28, 33)
        page.lineTo(9, 33)
        page.quadTo(7, 33, 7, 31)
        page.lineTo(7, 5)
        page.quadTo(7, 3, 9, 3)
        page.closeSubpath()
        painter.setPen(QPen(QColor(color).darker(120), 1.4))
        painter.setBrush(QColor("#ffffff"))
        painter.drawPath(page)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(color))
        painter.drawRoundedRect(QRectF(9, 19, 19, 10), 2, 2)
        painter.setPen(QPen(QColor("#ffffff")))
        font = QFont("Segoe UI", 6, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(QRectF(9, 19, 19, 10), Qt.AlignmentFlag.AlignCenter, label)
        painter.setPen(QPen(accent.lighter(135), 1.2))
        painter.drawLine(11, 13, 22, 13)
        painter.drawLine(11, 16, 25, 16)

    painter.end()
    icon = QIcon(pixmap)
    cache_key = ("folder" if kind == "folder" else label, color)
    _ICON_CACHE[cache_key] = icon
    return icon


def _entry_icon(name: str, is_directory: bool) -> QIcon:
    if is_directory:
        key = ("folder", "#f7c957")
        return _ICON_CACHE.get(key) or _draw_icon("folder", "", "#f7c957")
    extension = PurePath(name).suffix.lower().lstrip(".")
    label, color = _EXTENSION_LOOKUP.get(extension, ("FILE", "#718096"))
    key = (label, color)
    return _ICON_CACHE.get(key) or _draw_icon("file", label, color)


class DirectoryEntryDelegate(QStyledItemDelegate):
    """Draw recognizable file-type icons while retaining native row rendering."""

    def paint(self, painter, option, index) -> None:  # noqa: N802
        item_option = QStyleOptionViewItem(option)
        if index.column() == 0:
            name = str(index.data(Qt.ItemDataRole.DisplayRole) or "")
            is_directory = bool(index.data(Qt.ItemDataRole.UserRole + 1))
            item_option.icon = _entry_icon(name, is_directory)
        super().paint(painter, item_option, index)


class DirectoryListAppearance(QObject):
    """Apply the list style to current and later-created browser views."""

    def __init__(self, roots: list[QWidget], parent: QObject):
        super().__init__(parent)
        self._roots = roots
        self._refresh_pending = False
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)
        self.apply()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802
        if event.type() == QEvent.Type.ChildAdded and self._is_in_browser(watched):
            self._schedule_refresh()
        return False

    def _is_in_browser(self, obj: QObject) -> bool:
        current = obj if isinstance(obj, QWidget) else obj.parent()
        while isinstance(current, QWidget):
            if any(
                current is root or root.isAncestorOf(current)
                for root in self._roots
            ):
                return True
            current = current.parentWidget()
        return False

    def _schedule_refresh(self) -> None:
        if self._refresh_pending:
            return
        self._refresh_pending = True
        QTimer.singleShot(0, self.apply)

    def apply(self) -> None:
        self._refresh_pending = False
        for root in self._roots:
            for tree in root.findChildren(QTreeWidget):
                if tree.columnCount() != 5:
                    continue
                if tree.property("directoryListAppearanceInstalled"):
                    continue
                tree.setAlternatingRowColors(True)
                tree.setStyleSheet(_ROW_STYLE)
                tree.setIconSize(QSize(20, 20))
                tree.setItemDelegateForColumn(0, DirectoryEntryDelegate(tree))
                tree.setProperty("directoryListAppearanceInstalled", True)


def install_directory_list_appearance(window) -> None:
    """Install consistent styling in Directories and Files browser panes."""
    appearance = DirectoryListAppearance([window.directories, window.ftp], window)
    window._directory_list_appearance = appearance

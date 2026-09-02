from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget, QPushButton, QSplitter, QTextBrowser, QVBoxLayout

from hpc_gui.core.i18n import subscribe_language_change, t, unsubscribe_language_change
from hpc_gui.core.platform import current_os
from hpc_gui.services.help_catalog import HELP_CATALOG
from hpc_gui.services.help_search import HelpSearchIndex
from hpc_gui.services.shortcut_preferences import ShortcutPreferences


class HelpDialog(QDialog):
    """Qt presentation of the shared left-navigation/right-content Help Center."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("help.help_title"))
        self.setMinimumSize(820, 620)
        self.catalog = HELP_CATALOG
        self.search_index = HelpSearchIndex(self.catalog)
        self.shortcuts = ShortcutPreferences(current_os())
        self.current_topic_id = self.catalog.navigation()[0].id

        layout = QVBoxLayout(self)
        header = QHBoxLayout()
        header.addWidget(QLabel(t("help.help_title")))
        self.search = QLineEdit()
        self.search.setPlaceholderText(t("help.search_placeholder"))
        header.addWidget(self.search, 1)
        layout.addLayout(header)

        self.splitter = QSplitter(Qt.Horizontal)
        self.sidebar = QListWidget()
        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(False)
        self.splitter.addWidget(self.sidebar)
        self.splitter.addWidget(self.browser)
        self.splitter.setSizes([240, 580])
        layout.addWidget(self.splitter, 1)

        close = QPushButton(t("common.close"))
        close.clicked.connect(self.accept)
        layout.addWidget(close, 0, Qt.AlignRight)
        self.navigation = self.catalog.navigation()
        self.sidebar.currentRowChanged.connect(self._select_row)
        self.search.textChanged.connect(self._search)
        subscribe_language_change(self._language_changed)
        self.destroyed.connect(lambda: unsubscribe_language_change(self._language_changed))
        self._refresh_labels()

    def _binding(self, command_id: str) -> str | None:
        return next((item.binding for item in self.shortcuts.bindings() if item.command_id == command_id), None)

    def _refresh_labels(self, _language=None):
        selected = self.current_topic_id
        self.setWindowTitle(t("help.help_title"))
        self.search.setPlaceholderText(t("help.search_placeholder"))
        self.sidebar.blockSignals(True)
        self.sidebar.clear()
        self.sidebar.addItems([item.title() for item in self.navigation])
        self.sidebar.setCurrentRow(next((index for index, item in enumerate(self.navigation) if item.id == selected), 0))
        self.sidebar.blockSignals(False)
        self._render()

    def _language_changed(self, _language):
        self._refresh_labels(_language)

    def _select_row(self, row: int):
        if 0 <= row < len(self.navigation):
            self.current_topic_id = self.navigation[row].id
            self._render()

    def _search(self, query: str):
        results = self.search_index.search(query, platform=current_os())
        if results:
            result = results[0]
            if result.kind == "topic" and any(item.id == result.id for item in self.navigation):
                self.current_topic_id = result.id
                self._refresh_labels()
            else:
                self.browser.setPlainText(result.body)

    def _render(self):
        self.browser.setMarkdown(self.catalog.render_page(self.current_topic_id, current_os(), self._binding))

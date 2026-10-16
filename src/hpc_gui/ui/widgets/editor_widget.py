from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTabWidget
)

from hpc_gui.core.i18n import t
from hpc_gui.core.platform import current_os
from hpc_gui.services.shortcut_preferences import active_binding
from hpc_gui.ui.widgets.editor_document_actions import EditorDocumentActionsMixin
from hpc_gui.ui.widgets.editor_linting import EditorLintingMixin
from hpc_gui.ui.widgets.editor_templates import EditorTemplatesMixin
from hpc_gui.ui.widgets.editor_remote_io import EditorRemoteIoMixin
from hpc_gui.ui.widgets.editor_document_view import _EditorDocument




class EditorWidget(
    EditorDocumentActionsMixin,
    EditorLintingMixin,
    EditorTemplatesMixin,
    EditorRemoteIoMixin,
    QWidget,
):
    script_submitted = Signal(str, str)  # job_id, script_path
    run_in_terminal_requested = Signal(str)

    def __init__(self):
        super().__init__()
        self.session = None
        self.current_path: str | None = None

        self.path_in = QLineEdit()
        self.path_in.setPlaceholderText(t("placeholders.script_path"))
        self.path_in.returnPressed.connect(self.load_path)

        self.btn_load = QPushButton(t("editor.open"))
        self.btn_save = QPushButton(t("editor.save"))
        self.btn_new_template = QPushButton(
            t("editor.new_from_template")
            if t("editor.new_from_template") != "[editor.new_from_template]"
            else "New from Template..."
        )
        self.btn_save_submit = QPushButton(t("editor.save_submit") if t("editor.save_submit") != "[editor.save_submit]" else "Save + Submit")
        self.btn_save_run = QPushButton(t("editor.save_run") if t("editor.save_run") != "[editor.save_run]" else "Save + Run")
        self.btn_lint = QPushButton(t("editor.lint") if t("editor.lint") != "[editor.lint]" else "Lint")
        self.btn_array = QPushButton(t("editor.array") if t("editor.array") != "[editor.array]" else "Array...")

        self.btn_load.clicked.connect(self.load_path)
        self.btn_save.clicked.connect(self.save_path)
        self.btn_new_template.clicked.connect(self.new_from_template)
        self.btn_save_submit.clicked.connect(lambda: self.save_path(force_submit=True))
        self.btn_save_run.clicked.connect(lambda: self.save_path(run_in_terminal=True))
        self.btn_lint.clicked.connect(self.run_lint)
        self.btn_array.clicked.connect(self.edit_array)

        top = QHBoxLayout()
        self.lbl_remote = QLabel(t("editor.remote"))
        top.addWidget(self.lbl_remote)
        top.addWidget(self.path_in, 1)
        top.addWidget(self.btn_load)
        top.addWidget(self.btn_new_template)
        top.addWidget(self.btn_lint)
        top.addWidget(self.btn_array)
        top.addWidget(self.btn_save)
        top.addWidget(self.btn_save_submit)
        top.addWidget(self.btn_save_run)

        self.document_tabs = QTabWidget()
        self.document_tabs.setTabsClosable(True)
        self.document_tabs.setMovable(True)
        self.document_tabs.currentChanged.connect(self._on_current_document_changed)
        self.document_tabs.tabCloseRequested.connect(self._close_document_tab)
        self._add_document()
        self._last_find_query = ""
        self.find_bar = QWidget()
        self.find_bar.setVisible(False)
        find_layout = QHBoxLayout(self.find_bar)
        find_layout.setContentsMargins(0, 0, 0, 0)
        self.find_in = QLineEdit()
        self.find_in.setPlaceholderText(t("editor.find_placeholder"))
        self.replace_in = QLineEdit()
        self.replace_in.setPlaceholderText(t("editor.replace_placeholder"))
        self.btn_find_next = QPushButton(t("editor.find_next"))
        self.btn_replace = QPushButton(t("editor.replace"))
        self.btn_replace_all = QPushButton(t("editor.replace_all"))
        self.btn_find_close = QPushButton(t("common.close"))
        self.find_in.returnPressed.connect(self.find_next)
        self.btn_find_next.clicked.connect(self.find_next)
        self.btn_replace.clicked.connect(self.replace_current)
        self.btn_replace_all.clicked.connect(self.replace_all)
        self.btn_find_close.clicked.connect(self.find_bar.hide)
        find_layout.addWidget(QLabel(t("editor.find_label")))
        find_layout.addWidget(self.find_in, 1)
        find_layout.addWidget(QLabel(t("editor.replace_label")))
        find_layout.addWidget(self.replace_in, 1)
        find_layout.addWidget(self.btn_find_next)
        find_layout.addWidget(self.btn_replace)
        find_layout.addWidget(self.btn_replace_all)
        find_layout.addWidget(self.btn_find_close)
        self._shortcuts: list[QShortcut] = []
        self._install_shortcuts()

        lay = QVBoxLayout(self)
        lay.addLayout(top)
        lay.addWidget(self.find_bar)
        lay.addWidget(self.document_tabs)

    def _add_shortcut(self, sequence, callback) -> None:
        shortcut = QShortcut(QKeySequence(sequence), self)
        shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
        shortcut.activated.connect(callback)
        self._shortcuts.append(shortcut)

    def _install_shortcuts(self) -> None:
        self._add_shortcut("Ctrl+N", self.new_document)
        self._add_shortcut("Ctrl+S", self.save_path)
        self._add_shortcut("Ctrl+Shift+S", lambda: self.save_path(force_submit=True))
        self._add_shortcut("Ctrl+Enter", self.execute_active)
        self._add_shortcut("Ctrl+Z", lambda: self.text.undo())
        self._add_shortcut("Ctrl+Y", lambda: self.text.redo())
        self._add_shortcut("Ctrl+X", lambda: self.text.cut())
        self._add_shortcut("Ctrl+C", lambda: self.text.copy())
        self._add_shortcut("Ctrl+V", lambda: self.text.paste())
        self._add_shortcut("Ctrl+A", lambda: self.text.selectAll())
        self._add_shortcut("Ctrl+F", self.find_text)
        self._add_shortcut("Ctrl+H", self.find_text)
        self._add_shortcut("F3", self.find_next)
        self._add_shortcut("F8", self.run_lint)
        self._add_shortcut("Shift+F8", self.run_lint)
        self._add_shortcut("Ctrl+O", self.focus_open_path)
        self._add_shortcut("Ctrl+W", self.close_active_tab)
        self._add_shortcut("Ctrl+Tab", lambda: self.switch_document(1))
        self._add_shortcut("Ctrl+Shift+Tab", lambda: self.switch_document(-1))






















    def set_session(self, session):
        self.session = session

    def open_file(self, path: str, content: str, is_local: bool = False):
        existing = self._document_index_for_path(path)
        if existing >= 0:
            self.document_tabs.setCurrentIndex(existing)
            document = self.document_tabs.widget(existing)
            if isinstance(document, _EditorDocument):
                document.is_local = is_local
            return
        current = self._current_document()
        if (
            current is not None
            and not current.path
            and not current.text.toPlainText()
            and self.document_tabs.count() == 1
        ):
            current.path = path
            current.is_local = is_local
            current.saved_text = content
            current.text.setPlainText(content)
            index = self.document_tabs.indexOf(current)
            self.document_tabs.setTabText(index, self._tab_title(path))
            self.document_tabs.setTabToolTip(index, path)
            self._on_current_document_changed(index)
            return
        self._add_document(path, content, is_local=is_local)

    def open_local_file(self, path: str) -> None:
        """Open a local filesystem file for in-app editing (no session)."""
        text = Path(path).read_text(encoding="utf-8")
        self.open_file(path, text, is_local=True)

    def retranslate_ui(self):
        self.lbl_remote.setText(t("editor.remote"))
        self.btn_load.setText(t("editor.open"))
        self.btn_new_template.setText(
            t("editor.new_from_template")
            if t("editor.new_from_template") != "[editor.new_from_template]"
            else "New from Template..."
        )
        self.btn_lint.setText(t("editor.lint") if t("editor.lint") != "[editor.lint]" else "Lint")
        self.btn_array.setText(t("editor.array") if t("editor.array") != "[editor.array]" else "Array...")
        self.btn_save.setText(t("editor.save"))
        self.btn_save_submit.setText(t("editor.save_submit") if t("editor.save_submit") != "[editor.save_submit]" else "Save + Submit")
        self.btn_save_run.setText(t("editor.save_run") if t("editor.save_run") != "[editor.save_run]" else "Save + Run")
        for button, command in ((self.btn_save_submit, "EDIT-EXECUTE"), (self.btn_save_run, "EDIT-EXECUTE")):
            binding = active_binding(command, current_os())
            button.setToolTip(f"{button.text()} ({binding})" if binding else button.text())
        self.path_in.setPlaceholderText(t("placeholders.script_path"))
        self.find_in.setPlaceholderText(t("editor.find_placeholder"))
        self.replace_in.setPlaceholderText(t("editor.replace_placeholder"))
        self.btn_find_next.setText(t("editor.find_next"))
        self.btn_replace.setText(t("editor.replace"))
        self.btn_replace_all.setText(t("editor.replace_all"))
        self.btn_find_close.setText(t("common.close"))
        for index in range(self.document_tabs.count()):
            document = self.document_tabs.widget(index)
            if isinstance(document, _EditorDocument) and not document.path:
                self.document_tabs.setTabText(index, self._tab_title(""))

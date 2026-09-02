from __future__ import annotations

import posixpath
import re
from pathlib import Path

from PySide6.QtCore import QEvent, Signal, Qt
from PySide6.QtGui import QKeySequence, QShortcut, QTextCursor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTextEdit, QMessageBox, QTabWidget
)

from hpc_gui.core.i18n import t
from hpc_gui.core.platform import current_os
from hpc_gui.services.shortcut_preferences import active_binding
from hpc_gui.services.editor_controller import EditorCommandService
from hpc_gui.core.ui_errors import show_exception
from hpc_gui.core.history import append_event
from hpc_gui.ui.dialogs.slurm_array_dialog import edit_slurm_array


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


class EditorWidget(QWidget):
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
        text = Path(path).read_text(encoding="utf-8", errors="replace")
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

    def run_lint(self):
        path = self.path_in.text().strip()
        text = self.text.toPlainText()
        if not path:
            QMessageBox.information(self, t("common.info"), t("editor.lint_need_path") if t("editor.lint_need_path") != "[editor.lint_need_path]" else "Please provide a target path first.")
            return
        issues = self._collect_lint_issues(path, text)
        diagnostics = self._run_plugin_lint(path, text)
        diagnostics = diagnostics + self._run_v2_tool_lint(path, text)
        diagnostics = diagnostics + self._run_cross_checks(text)
        if not issues and not diagnostics:
            QMessageBox.information(self, t("common.info"), t("editor.lint_ok") if t("editor.lint_ok") != "[editor.lint_ok]" else "Lint passed. No obvious issues found.")
            return
        self._show_lint_results(path, issues, diagnostics)

    def _run_cross_checks(self, text: str) -> list:
        """Static Slurm/Fluent resource-consistency checks on the same text."""
        from hpc_gui.lint.job_context import (
            cross_diagnostics,
            parse_fluent_launch,
            parse_slurm_context,
        )

        try:
            context = parse_slurm_context(text)
            launch = parse_fluent_launch(text)
            return cross_diagnostics(context, launch)
        except Exception:  # never break the editor on parse surprises
            return []

    def _run_plugin_lint(self, path: str, text: str) -> list:
        """Run installed declarative lint packs matching the file name."""
        from hpc_gui.lint.engine import LintError, lint_text
        from hpc_gui.lint.rulepack import load_lint_packs

        diagnostics = []
        try:
            packs = load_lint_packs()
        except Exception:
            return diagnostics
        matched = [pack for pack in packs if pack.matches(path)]
        for pack in matched:
            try:
                diagnostics.extend(lint_text(text, file_name=path, rule_pack=pack))
            except (LintError, Exception):  # noqa: B014 - never break the editor
                continue
        return diagnostics

    def _run_v2_tool_lint(self, path: str, text: str) -> list:
        """Run Plugin API v2 linter tools for the file suffix (additive)."""
        import logging

        try:
            from hpc_gui.lint.models import Diagnostic, Severity
            from hpc_gui.plugins.linter_tools import tools_supporting_suffix
        except Exception:
            return []
        suffix = Path(path).suffix.lower()
        if not suffix:
            return []
        try:
            tools = tools_supporting_suffix(suffix)
        except Exception:
            logging.getLogger(__name__).warning(
                "v2 lint tool lookup failed for %s", path, exc_info=True
            )
            return []
        if not tools:
            return []
        # Collect from every supporting tool; per-tool failures are contained.
        raw_diags: list[tuple] = []  # (tool, diag)
        for tool in tools:
            try:
                from hpc_gui.plugins.linter_tools import lint_text_with_tool_for

                run = lint_text_with_tool_for(tool, text, file_name=path)
            except Exception:
                logging.getLogger(__name__).warning(
                    "v2 lint failed for %s via %s", path, tool.plugin_id, exc_info=True
                )
                continue
            # lint_text_with_tool_for returns a FileResult (editor path);
            # be tolerant if a future wrapper returns a LintRunResult or list.
            diags: list = []
            if hasattr(run, "diagnostics"):
                diags = list(getattr(run, "diagnostics") or [])
            elif hasattr(run, "files"):
                for fr in getattr(run, "files") or []:
                    diags.extend(getattr(fr, "diagnostics", []) or [])
            elif isinstance(run, list):
                diags = run
            for diag in diags:
                raw_diags.append((tool, diag))
        if not raw_diags:
            return []
        # Deduplicate by (rule_id, line, column, message); sort by position.
        seen: set[tuple] = set()
        deduped: list[tuple] = []
        for tool, diag in raw_diags:
            key = (
                getattr(diag, "code", getattr(diag, "rule_id", "V2")),
                getattr(diag, "line", None),
                getattr(diag, "column", None),
                getattr(diag, "message", str(diag)),
            )
            if key in seen:
                continue
            seen.add(key)
            deduped.append((tool, diag))
        deduped.sort(
            key=lambda item: (
                getattr(item[1], "line", None) or 9999,
                getattr(item[1], "column", None) or 0,
                getattr(item[1], "code", getattr(item[1], "rule_id", "")),
            )
        )
        # When multiple tools contribute, prefix the message with the plugin id
        # so the result list stays attributable without changing the model shape.
        multi = len({t.plugin_id for t, _ in deduped}) > 1
        converted: list = []
        for tool, diag in deduped:
            try:
                severity_value = getattr(diag.severity, "value", str(diag.severity))
                severity = Severity(severity_value)
            except ValueError:
                severity = Severity.INFO
            raw_message = getattr(diag, "message", str(diag))
            message = f"[{tool.plugin_id}] {raw_message}" if multi else raw_message
            converted.append(
                Diagnostic(
                    rule_id=getattr(diag, "code", getattr(diag, "rule_id", "V2")),
                    severity=severity,
                    message=message,
                    line=getattr(diag, "line", None),
                    column=getattr(diag, "column", None),
                    end_line=getattr(diag, "end_line", getattr(diag, "endLine", None)),
                    end_column=getattr(diag, "end_column", getattr(diag, "endColumn", None)),
                    explanation=getattr(diag, "explanation", "") or "",
                    suggested_fix=getattr(diag, "suggested_fix", getattr(diag, "suggestedFix", "")) or "",
                    documentation_url=getattr(diag, "source_url", getattr(diag, "documentation_url", "")) or "",
                    plugin_id=getattr(tool, "plugin_id", ""),
                    plugin_version=getattr(tool, "version", ""),
                )
            )
        return converted

    def _show_lint_results(self, path: str, issues: list[str], diagnostics: list) -> None:
        """Show a diagnostics dialog; double-click navigates the editor line."""
        from PySide6.QtWidgets import QDialog, QListWidget, QListWidgetItem, QVBoxLayout
        from PySide6.QtGui import QTextCursor

        labels, positions = self._lint_result_entries(issues, diagnostics)

        dialog = QDialog(self)
        dialog.setWindowTitle(
            t("editor.lint_results_title")
            if t("editor.lint_results_title") != "[editor.lint_results_title]"
            else "Lint results"
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

    @staticmethod
    def _lint_result_entries(issues: list[str], diagnostics: list) -> tuple[list[str], list[int]]:
        """Build display labels and 0-based navigation lines (-1 = no target)."""
        labels: list[str] = []
        positions: list[int] = []
        for issue in issues:
            labels.append(f"- {issue}")
            positions.append(-1)
        for diagnostic in sorted(diagnostics, key=lambda d: (d.line or 0, d.column or 0)):
            location = f"{diagnostic.line}:{diagnostic.column}" if diagnostic.line else "-"
            severity = (
                diagnostic.severity.value
                if hasattr(diagnostic.severity, "value")
                else str(diagnostic.severity)
            )
            labels.append(f"[{location}] {severity}: {diagnostic.message} ({diagnostic.rule_id})")
            positions.append(max(0, (diagnostic.line or 1) - 1))
        return labels, positions

    def new_from_template(self):
        """Open the plugin-template browser; rendered text opens in a NEW
        document tab for review/editing. Nothing is saved or submitted
        automatically."""
        from hpc_gui.plugins.job_templates import load_job_templates

        try:
            templates = load_job_templates()
        except Exception:
            templates = []
        if not templates:
            QMessageBox.information(
                self,
                t("common.info"),
                t("templates.none_installed"),
            )
            return
        from PySide6.QtWidgets import QDialog
        from hpc_gui.ui.dialogs.template_browser_dialog import TemplateBrowserDialog

        provider_template = {}
        if isinstance(self.session, dict):
            cfg = self.session.get("cfg")
            provider_template = getattr(cfg, "provider_template", {}) or {}
            if isinstance(provider_template, dict):
                provider_template = dict(provider_template)
                provider_template["account"] = getattr(cfg, "account", "")
        dialog = TemplateBrowserDialog(self, templates, provider_template=provider_template)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        template, values = dialog.result_template, dialog.result_values
        if template is None:
            return
        from hpc_gui.plugins.job_templates import render_template

        try:
            rendered = render_template(template, values)
        except Exception as exc:
            QMessageBox.warning(self, t("common.error"), str(exc))
            return
        # Preview requirement: content lands in an unsaved editor tab.
        suggested = template.file_name or f"{template.id}.txt"
        self.open_file("", rendered)
        index = self.document_tabs.currentIndex()
        if index >= 0:
            self.document_tabs.setTabText(index, self._tab_title(suggested))
        document = self._current_document()
        if document is not None:
            document.path = ""

    def load_path(self):
        document = self._current_document()
        if document is not None and document.is_local:
            path = document.path
            try:
                content = Path(path).read_text(encoding="utf-8", errors="replace")
                document.text.setPlainText(content)
                append_event({"type": "editor_load", "path": path})
            except OSError as e:
                show_exception(self, title=t("common.error"), user_message=t("editor.open_failed").format(err=e), exc=e, area="EDITOR")
            return
        if not self.session or not self.session.get("files"):
            QMessageBox.warning(self, t("common.error"), t("common.no_connection"))
            return
        path = self.path_in.text().strip()
        if not path:
            return
        try:
            content = self.session["files"].read_text(path)
            self.open_file(path, content)
            append_event({"type": "editor_load", "path": path})
        except Exception as e:
            show_exception(self, title=t("common.error"), user_message=t("editor.open_failed").format(err=e), exc=e, area="EDITOR")

    def save_path(self, force_submit: bool = False, run_in_terminal: bool = False):
        document = self._current_document()
        path = self.path_in.text().strip()
        if document is not None and document.is_local:
            if not path:
                return
            text = self.text.toPlainText()
            if not self._validate_before_save(path, text):
                return
            try:
                Path(path).write_text(text, encoding="utf-8", newline="")
                self._set_active_document_path(path)
                document.saved_text = text
                document.text.document().setModified(False)
                append_event({"type": "editor_save", "path": path})
                if run_in_terminal and path.lower().endswith(".sh"):
                    self.run_in_terminal_requested.emit(path)
                    return
                QMessageBox.information(self, t("common.info"), t("editor.saved") if t("editor.saved") != "[editor.saved]" else "Saved.")
            except OSError as e:
                show_exception(self, title=t("common.error"), user_message=t("editor.save_failed").format(err=e), exc=e, area="EDITOR")
            return
        if not self.session or not self.session.get("files"):
            QMessageBox.warning(self, t("common.error"), t("common.no_connection"))
            return
        if not path:
            return
        text = self.text.toPlainText()
        if not self._validate_before_save(path, text):
            return
        try:
            self.session["files"].write_text(path, text)
            self._set_active_document_path(path)
            document.saved_text = text
            document.text.document().setModified(False)
            append_event({"type": "editor_save", "path": path})
            if run_in_terminal:
                if path.lower().endswith(".sh"):
                    self.run_in_terminal_requested.emit(path)
                return
            self._offer_submit_after_save(path, force_submit=force_submit)
        except Exception as e:
            show_exception(self, title=t("common.error"), user_message=t("editor.save_failed").format(err=e), exc=e, area="EDITOR")

    def _validate_before_save(self, path: str, text: str) -> bool:
        is_slurm = path.lower().endswith((".slurm", ".sbatch"))
        if not is_slurm:
            return True

        warnings = self._collect_lint_issues(path, text)

        if not warnings:
            return True

        message = (t("editor.validation_title") if t("editor.validation_title") != "[editor.validation_title]" else "Script validation warnings:") + "\n\n" + "\n".join(warnings)
        answer = QMessageBox.question(
            self,
            t("common.warning") if t("common.warning") != "[common.warning]" else "Warning",
            message + "\n\n" + (t("editor.validation_continue") if t("editor.validation_continue") != "[editor.validation_continue]" else "Save anyway?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return answer == QMessageBox.StandardButton.Yes

    def _offer_submit_after_save(self, path: str, *, force_submit: bool = False):
        is_slurm = path.lower().endswith((".slurm", ".sbatch"))
        if not is_slurm:
            QMessageBox.information(self, t("common.info"), t("editor.saved") if t("editor.saved") != "[editor.saved]" else "Saved.")
            return

        if not force_submit:
            answer = QMessageBox.question(
                self,
                t("editor.submit") if t("editor.submit") != "[editor.submit]" else "Submit (sbatch)",
                t("editor.ask_submit_after_save") if t("editor.ask_submit_after_save") != "[editor.ask_submit_after_save]" else "Saved. Submit to Slurm now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if answer != QMessageBox.StandardButton.Yes:
                QMessageBox.information(self, t("common.info"), t("editor.saved") if t("editor.saved") != "[editor.saved]" else "Saved.")
                return

        slurm = (self.session or {}).get("slurm")
        if not slurm:
            QMessageBox.warning(self, t("common.error"), t("common.no_connection"))
            return
        try:
            out = slurm.sbatch(path)
            append_event({"type": "editor_submit", "path": path, "result": out})
            job_id = self._extract_job_id(out)
            if job_id:
                self.script_submitted.emit(job_id, path)
                msg = (t("editor.submitted_job") if t("editor.submitted_job") != "[editor.submitted_job]" else "Submitted. Job ID: {jobid}").format(jobid=job_id)
                QMessageBox.information(self, t("common.info"), msg + "\n" + (out or ""))
            else:
                # sbatch can fail and still return output text. Show actionable error.
                details = out or ""
                hint = self._diagnose_submit_output(details)
                QMessageBox.critical(
                    self,
                    t("common.error"),
                    (t("editor.submit_failed") if t("editor.submit_failed") != "[editor.submit_failed]" else "Submission failed.") + "\n\n" + hint + ("\n\n" + details if details else ""),
                )
        except Exception as e:
            show_exception(self, title=t("common.error"), user_message=t("editor.submit_error").format(err=e), exc=e, area="SLURM")

    @staticmethod
    def _extract_job_id(sbatch_output: str) -> str:
        txt = sbatch_output or ""
        m = re.search(r"Submitted batch job\s+(\d+)", txt, flags=re.IGNORECASE)
        if m:
            return m.group(1)
        return ""

    def _collect_lint_issues(self, path: str, text: str) -> list[str]:
        issues: list[str] = []
        is_slurm = path.lower().endswith((".slurm", ".sbatch"))
        if not is_slurm:
            return issues
        stripped = text.lstrip()
        if not stripped.startswith("#!"):
            issues.append(t("editor.validation_missing_shebang") if t("editor.validation_missing_shebang") != "[editor.validation_missing_shebang]" else "- Missing shebang (e.g. #!/bin/bash)")
        if "#SBATCH" not in text:
            issues.append(t("editor.validation_missing_sbatch") if t("editor.validation_missing_sbatch") != "[editor.validation_missing_sbatch]" else "- No #SBATCH directives found")
        if "USERNAME" in text or "<partition>" in text:
            issues.append(t("editor.validation_placeholders") if t("editor.validation_placeholders") != "[editor.validation_placeholders]" else "- Template placeholders detected (USERNAME / <partition>)")
        if "--time=" not in text and "\n#SBATCH -t " not in text:
            issues.append(t("editor.validation_missing_time") if t("editor.validation_missing_time") != "[editor.validation_missing_time]" else "- Time limit is not set (#SBATCH --time or -t)")
        if "--output=" not in text and "\n#SBATCH -o " not in text:
            issues.append(t("editor.validation_missing_output") if t("editor.validation_missing_output") != "[editor.validation_missing_output]" else "- Output file is not set (#SBATCH --output or -o)")
        return issues

    def _diagnose_submit_output(self, details: str) -> str:
        msg = (details or "").lower()
        if "invalid account" in msg:
            return t("editor.submit_hint_account") if t("editor.submit_hint_account") != "[editor.submit_hint_account]" else "Invalid account/partition combination. Verify #SBATCH -A and -p values."
        if "invalid qos" in msg or "qos" in msg and "invalid" in msg:
            return t("editor.submit_hint_qos") if t("editor.submit_hint_qos") != "[editor.submit_hint_qos]" else "QOS is invalid for this account. Try another QOS/partition."
        if "time limit" in msg or "walltime" in msg or "qosmaxwalldurationperjoblimit" in msg:
            return t("editor.submit_hint_time") if t("editor.submit_hint_time") != "[editor.submit_hint_time]" else "Requested time is above policy limits. Lower --time or change QOS."
        if "more processors requested than permitted" in msg or "assocmaxcpuperjoblimit" in msg:
            return t("editor.submit_hint_cpu") if t("editor.submit_hint_cpu") != "[editor.submit_hint_cpu]" else "CPU request exceeds allowed limit. Reduce -c/-n or ask for higher limits."
        if "gres" in msg and ("invalid" in msg or "requested node configuration is not available" in msg):
            return t("editor.submit_hint_gpu") if t("editor.submit_hint_gpu") != "[editor.submit_hint_gpu]" else "GPU request may be invalid for selected partition. Check --gres and partition."
        return t("editor.submit_failed_hint") if t("editor.submit_failed_hint") != "[editor.submit_failed_hint]" else "Check account/partition/time/memory and script directives."

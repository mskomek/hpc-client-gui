"""Qt OpenFOAM case workspace following the three-column studio layout.

Host-owned PySide6 page. All parsing, saving, recovery, catalog, and
script state reuse the application-owned workspace/model/business
services; this module only wires Qt widgets to them. Never imports
candidate package Python. Remote state always comes from the live
application session and is never invented.
"""

from __future__ import annotations

from difflib import unified_diff
from pathlib import Path, PurePosixPath

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QShortcut
from PySide6.QtWidgets import (
    QFileDialog,
    QMessageBox,
    QPlainTextEdit,
    QTreeWidgetItem,
    QWidget,
)

from hpc_gui.core.i18n import tr
from hpc_gui.openfoam_core import preferred_newline

from .command_catalog import load_command_catalog
from .qt_actions import QtCaseManagerActions, QtCaseSaveActions, _case_root_for_selection, _session_files
from .qt_inspector import QtTypedInspector
from .qt_job_draft import open_job_draft
from .qt_review import store_reviewed_allrun, validate_case
from .qt_view import QtCaseStudioView
from .workspace import CaseWorkspace
from .workflow import WorkflowPlan


class QtCaseStudioPage(QWidget, QtCaseStudioView):
    def __init__(
        self,
        parent=None,
        *,
        plugin,
        session_state=None,
        initial_path=None,
        remote: bool = False,
        action=None,
    ):
        super().__init__(parent)
        self.plugin = plugin
        self.session_state = dict(session_state or {})
        self.workspace: CaseWorkspace | None = None
        self.remote = False
        self.documents: dict = {}
        self.command_catalog = load_command_catalog(plugin)
        self.workflow_plan = WorkflowPlan(self.command_catalog["commands"])
        self._editors: dict[str, QPlainTextEdit] = {}
        self._loading = False
        self.last_error = ""
        self._build()
        self.save_actions = QtCaseSaveActions(self)
        self.case_manager_actions = QtCaseManagerActions(self)
        self.case_manager_actions.bind()
        self.inspector = QtTypedInspector(
            key_list=self.key_list,
            editor_panel=self.value_editor_panel,
            editor_layout=self.value_editor_layout,
            type_label=self.parameter_type,
            apply_button=self.apply_value,
            status=self.status,
            current_document=self._current_document,
            on_replace=self._inspector_replaced,
        )
        self._bind()
        self._show_commands()
        self._refresh_flow()
        if initial_path:
            self.open_target(str(initial_path), remote=remote, action=action)
        elif action == "new" and not remote:
            QTimer.singleShot(0, self.case_manager_actions._new_case)
        elif action == "draft":
            QTimer.singleShot(0, lambda: open_job_draft(self))

    # -- wiring ---------------------------------------------------------
    def _bind(self):
        self.save_button.clicked.connect(self._save)
        self.recover_button.clicked.connect(self._recover_save)
        self.validate_button.clicked.connect(self._validate)
        self.allrun_button.clicked.connect(self._create_allrun)
        self.undo_button.clicked.connect(lambda _checked=False: self._edit_command("Undo"))
        self.redo_button.clicked.connect(lambda _checked=False: self._edit_command("Redo"))
        self.tree.itemClicked.connect(self._tree_selected)
        self.source_tabs.tabCloseRequested.connect(self._close_tab)
        self.source_tabs.currentChanged.connect(lambda _index=0: self._refresh_inspector())
        self.command_filter.textChanged.connect(lambda _text="": self._show_commands())
        self.commands.itemClicked.connect(self._command_selected)
        self.add_step.clicked.connect(self._add_selected_step)
        self.remove_step.clicked.connect(self._remove_selected_step)
        self.move_step_up.clicked.connect(lambda _checked=False: self._move_selected_step(-1))
        self.move_step_down.clicked.connect(lambda _checked=False: self._move_selected_step(1))
        self.flow.itemClicked.connect(self._flow_selected)
        for sequence, name in (("Ctrl+Z", "Undo"), ("Ctrl+Y", "Redo"), ("Ctrl+Shift+Z", "Redo")):
            shortcut = QShortcut(sequence, self)
            shortcut.setContext(Qt.WidgetWithChildrenShortcut)
            shortcut.activated.connect(lambda n=name: self._edit_command(n))

    # -- case open ------------------------------------------------------
    def open_target(self, path: str, *, remote: bool = False, action=None, read_only: bool = False):
        if action == "new" and not remote:
            QTimer.singleShot(0, lambda: self.case_manager_actions.create_new_case_at(str(path)))
            return
        if remote:
            self._open_remote_target(path, action=action, read_only=read_only)
            return
        candidate = Path(path).expanduser()
        case_root = _case_root_for_selection(candidate)
        try:
            workspace = CaseWorkspace(str(case_root), read_only=read_only)
            self._install_workspace(workspace)
            if candidate.is_file():
                self._open_document(str(candidate))
            if action == "draft":
                QTimer.singleShot(0, lambda: open_job_draft(self))
        except Exception as exc:
            self._show_error(f"Could not open case: {exc}")

    def _open_remote_target(self, path: str, *, action=None, read_only: bool = False):
        files = _session_files(self.session_state)
        if files is None:
            reason = "Remote case is unavailable: no authenticated session"
            self.status.setText(reason)
            self.last_error = reason
            return
        remote = PurePosixPath(path)
        selected_file: PurePosixPath | None = None
        try:
            is_directory = bool(files.is_dir(str(remote)))
            if not is_directory:
                selected_file = remote
        except Exception:
            is_directory = False
            selected_file = remote
        case_roots = {"system", "constant", "0", "0.orig"}
        parts = remote.parts
        base_index = next((i for i, part in enumerate(parts) if part in case_roots), None)
        if base_index is not None:
            remote = PurePosixPath(*parts[:base_index])
        elif not is_directory or remote.name in case_roots:
            remote = remote.parent
        self.status.setText("Loading remote case ...")
        try:
            workspace = CaseWorkspace(str(remote), remote=True, files=files, read_only=read_only)
        except Exception as exc:
            self._show_error(f"Could not open case: {exc}")
            return
        self._install_workspace(workspace)
        if selected_file is not None:
            self._open_document(str(selected_file))
        if action == "draft":
            QTimer.singleShot(0, lambda: open_job_draft(self))

    def _install_workspace(self, workspace: CaseWorkspace):
        while self.source_tabs.count():
            self.source_tabs.removeTab(0)
        self._editors.clear()
        self.workspace = workspace
        self.remote = workspace.remote
        self.documents = workspace.documents
        self.save_actions.workspace_changed(workspace)
        self._populate_tree()
        self._refresh_preview()
        self._refresh_problems()
        self._refresh_diff()
        self.save_button.setEnabled(not workspace.read_only)
        self.undo_button.setEnabled(not workspace.read_only)
        self.redo_button.setEnabled(not workspace.read_only)
        self.allrun_button.setEnabled(not workspace.read_only)
        self.case_manager_actions.refresh_search()
        mode = "Remote" if self.remote else "Local"
        if workspace.read_only:
            mode = f"{mode} (read-only snapshot)"
        self.status.setText(f"Case opened: {workspace.root} [{mode}]")

    # -- tree and search -------------------------------------------------
    def _populate_tree(self):
        self.tree.clear()
        root_label = self.workspace.root if self.workspace else "Case structure"
        root = QTreeWidgetItem([root_label])
        self.tree.addTopLevelItem(root)
        if self.workspace is None:
            root.setExpanded(True)
            return
        nodes: dict[str, QTreeWidgetItem] = {"": root}
        for item in self.workspace.paths:
            clean = item.rstrip("/")
            parent_path = str(PurePosixPath(clean).parent)
            parent_path = "" if parent_path == "." else parent_path
            name = PurePosixPath(clean).name
            parent_item = nodes.get(parent_path, root)
            created = QTreeWidgetItem([name])
            parent_item.addChild(created)
            if item.endswith("/"):
                nodes[clean] = created
            else:
                created.setData(0, Qt.ItemDataRole.UserRole, clean)
        root.setExpanded(True)

    def _tree_selected(self, item, _column=0):
        relative = item.data(0, Qt.ItemDataRole.UserRole)
        if relative:
            self._open_document(relative)

    # -- documents -------------------------------------------------------
    def _open_document(self, target: str):
        if self.workspace is None:
            return
        try:
            document = self.workspace.open_dictionary(target)
        except Exception as exc:
            self._show_error(f"Could not open dictionary: {exc}")
            return
        known = {
            self.source_tabs.indexOf(editor): relative
            for relative, editor in self._editors.items()
            if self.source_tabs.indexOf(editor) >= 0
        }
        for index in range(self.source_tabs.count()):
            if known.get(index) == document.relative_path:
                self.source_tabs.setCurrentIndex(index)
                return
        editor = QPlainTextEdit()
        editor.setPlainText(document.text)
        editor.setReadOnly(document.read_only)
        editor.textChanged.connect(lambda doc=document, ctl=editor: self._source_changed(doc, ctl))
        self._editors[document.relative_path] = editor
        label = Path(document.relative_path).name + (" *" if document.modified else "")
        self.source_tabs.addTab(editor, label)
        self.source_tabs.setCurrentWidget(editor)
        self._refresh_inspector(document)
        self._refresh_diff()
        self._refresh_problems()

    def _close_tab(self, index: int):
        widget = self.source_tabs.widget(index)
        relative = next((name for name, editor in self._editors.items() if editor is widget), None)
        if relative is not None:
            document = self.documents.get(relative)
            if document is not None and document.modified:
                if not self.save_actions.confirm_discard(
                    "Close Tab", f"Discard unsaved edits to {relative}?"
                ):
                    return
            del self._editors[relative]
        self.source_tabs.removeTab(index)
        self._refresh_inspector()

    def _current_document(self):
        widget = self.source_tabs.currentWidget()
        if widget is None:
            return None
        return next(
            (doc for doc in self.documents.values() if self._editors.get(doc.relative_path) is widget),
            None,
        )

    def _source_changed(self, document, control):
        if self._loading or (self.workspace is not None and self.workspace.read_only):
            return
        editor_text = control.toPlainText().replace("\r\n", "\n").replace("\r", "\n")
        try:
            document.set_text(editor_text.replace("\n", preferred_newline(document.decoded.text)))
        except PermissionError as exc:
            self._show_error(str(exc))
            return
        for index in range(self.source_tabs.count()):
            if self.source_tabs.widget(index) is control:
                label = Path(document.relative_path).name + (" *" if document.modified else "")
                self.source_tabs.setTabText(index, label)
                break
        self._refresh_diff()
        self._refresh_problems()
        self._refresh_inspector(document)

    def _refresh_inspector(self, document=None):
        self.inspector.refresh(document or self._current_document())

    def _inspector_replaced(self, document, _entry, updated):
        if document.read_only:
            return
        editor = self._editors.get(document.relative_path)
        if editor is None:
            return
        document.set_text(updated)
        self._loading = True
        try:
            editor.setPlainText(updated)
        finally:
            self._loading = False
        self._source_changed(document, editor)

    # -- problems / diff / preview ---------------------------------------
    def _refresh_problems(self, document=None):
        selected = (document,) if document else tuple(self.documents.values())
        values = []
        for item in selected:
            for issue in item.parsed.diagnostics:
                values.append(
                    f"{issue.severity.upper()} {issue.rule_id} "
                    f"{issue.path}:{issue.line}:{issue.column} {issue.message}"
                )
        self.problems.clear()
        self.problems.addItems(values or ["No findings"])

    def _refresh_diff(self):
        lines: list[str] = []
        for relative, document in self.documents.items():
            if not document.modified:
                continue
            lines.extend(
                unified_diff(
                    document.decoded.text.splitlines(True),
                    document.text.splitlines(True),
                    fromfile=relative,
                    tofile=relative + " (edited)",
                )
            )
        self.diff.setPlainText("".join(lines) or "No unsaved changes")

    def _refresh_preview(self):
        if self.workspace is None:
            self.preview.setPlainText("No case open")
            return
        control = self.documents.get("system/controlDict")
        solver = control.parsed.value("application") if control else None
        solver = solver or "unknown solver"
        try:
            region_properties = self.workspace.region_properties
            region_summary = (
                "no regions declared" if region_properties is None else region_properties.summary
            )
        except ValueError:
            region_summary = "regions unresolved"
        self.preview.setPlainText(
            "OpenFOAM.com / ESI\n"
            "v2312\n"
            f"Case root: {self.workspace.root}\n"
            f"Solver: {solver}\n"
            f"Dictionaries: {len(self.documents)}\n"
            f"Regions: {region_summary}\n"
            f"Modified files: {len(self.workspace.modified_paths())}\n"
            "Runtime: draft only (nothing is executed)"
        )

    # -- save / validate / allrun -----------------------------------------
    def _save(self, _checked=False):
        self.save_actions.save()

    def _recover_save(self, _checked=False):
        self.save_actions.recover()

    def _validate(self, _checked=False):
        validate_case(self)

    def _create_allrun(self, _checked=False):
        store_reviewed_allrun(self)

    # -- undo / redo ------------------------------------------------------
    def _edit_command(self, name: str):
        if self.workspace is not None and self.workspace.read_only:
            return
        document = self._current_document()
        if document is None:
            return
        changed = document.undo() if name == "Undo" else document.redo()
        if not changed:
            return
        control = self._editors.get(document.relative_path)
        if control is None:
            return
        self._loading = True
        try:
            control.setPlainText(document.text)
        finally:
            self._loading = False
        self._source_changed(document, control)

    # -- workflow ----------------------------------------------------------
    def _show_commands(self):
        query = self.command_filter.text().strip().lower()
        self.commands.clear()
        for command in self.command_catalog["commands"]:
            name = str(command.get("name", ""))
            if query and query not in name.lower():
                continue
            self.commands.addItem(f"{name}  —  {command.get('verification_status', '')}")

    def _command_selected(self, _item=None):
        name = self._take_item_text(self.commands.currentItem()).split("  —  ")[0].strip()
        for command in self.command_catalog["commands"]:
            if str(command.get("name")) == name:
                self.command_details.setPlainText(
                    f"{name}\ncategory: {command.get('category', '')}\n"
                    f"status: {command.get('verification_status', '')}\n"
                    f"execution: {command.get('execution', '')}"
                )
                return

    def _add_selected_step(self, _checked=False):
        if self.workspace is not None and self.workspace.read_only:
            return
        name = self._take_item_text(self.commands.currentItem()).split("  —  ")[0].strip()
        if not name:
            return
        try:
            self.workflow_plan.add(name)
        except (ValueError, IndexError) as exc:
            self._show_error(str(exc))
            return
        self._refresh_flow()

    def _remove_selected_step(self, _checked=False):
        index = self.flow.currentRow()
        if index < 0:
            return
        try:
            self.workflow_plan.remove(index)
        except IndexError as exc:
            self._show_error(str(exc))
            return
        self._refresh_flow()

    def _move_selected_step(self, offset: int):
        index = self.flow.currentRow()
        if index < 0:
            return
        try:
            moved = self.workflow_plan.move(index, offset)
        except (IndexError, ValueError) as exc:
            self._show_error(str(exc))
            return
        if moved is not None:
            self.flow.setCurrentRow(moved)
        self._refresh_flow()

    def _flow_selected(self, _item=None):
        self._refresh_flow()

    def _refresh_flow(self):
        selected = self.flow.currentRow()
        self.flow.clear()
        self.flow.addItems(list(self.workflow_plan.labels()))
        if 0 <= selected < self.flow.count():
            self.flow.setCurrentRow(selected)

    # -- errors -------------------------------------------------------------
    def _show_error(self, message: str):
        self.last_error = str(message)
        self.status.setText(str(message))
        notice = QMessageBox(self)
        notice.setWindowTitle(tr("openfoam.title", "OpenFOAM Case Studio"))
        notice.setText(str(message))
        notice.setIcon(QMessageBox.Warning)
        notice.setAttribute(Qt.WA_DeleteOnClose)
        notice.show()

    def open_local_directory(self) -> str:
        selected = QFileDialog.getExistingDirectory(
            self, "Open Case", "", QFileDialog.ShowDirsOnly
        )
        if selected:
            self.open_target(selected)
        return selected


def create_qt_page(
    parent=None, *, plugin, session_state=None, initial_path=None, remote=False, action=None
):
    """Build the host-owned Qt Case Studio page (never candidate code)."""
    page = QtCaseStudioPage(
        parent,
        plugin=plugin,
        session_state=session_state,
        initial_path=initial_path,
        remote=remote,
        action=action,
    )
    page._hpc_trusted_tool_controller = page
    return page

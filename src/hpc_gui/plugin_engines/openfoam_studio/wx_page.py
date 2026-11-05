"""wx OpenFOAM case workspace following the Journal Studio three-column layout."""
from __future__ import annotations

from difflib import unified_diff
from pathlib import Path, PurePosixPath
from threading import Thread

from hpc_gui.core.i18n import t
from hpc_gui.openfoam_core import preferred_newline

from .command_catalog import load_command_catalog
from .workspace import CaseWorkspace
from .wx_view import WxCaseStudioView
from .release_selection import ReleaseSelectionController
from .workflow import WorkflowPlan
from .run_script import render_allrun
from .wx_workflow import WxCommandWorkflow
from .wx_inspector import WxTypedInspector
from .wx_case_manager_actions import WxCaseManagerActions
from .wx_save_actions import WxCaseSaveActions


def _case_root_for_selection(candidate: Path) -> Path:
    """Resolve a selected dictionary or case subfolder to its case root."""
    selected = candidate.resolve(strict=False)
    if selected.is_file():
        selected = selected.parent
    for parent in (selected, *selected.parents):
        if any((parent / name).is_dir() for name in ("system", "constant", "0")):
            return parent
    return selected


class WxCaseStudioPage(WxCaseStudioView):
    def __init__(self, parent, *, plugin, session_state=None, initial_path=None, remote=False, action=None):
        import wx

        self.wx = wx
        self.plugin = plugin
        self.target_release = "v2312"
        self.session_state = session_state or {}
        self.workspace = None
        self.remote = False
        self.documents = {}
        self.command_catalog = load_command_catalog(plugin)
        self.workflow_plan = WorkflowPlan(self.command_catalog["commands"])
        self._tree_paths = {}
        self._editors = {}
        self._loading = False
        self.panel = wx.Panel(parent)
        self._build()
        self.save_actions = WxCaseSaveActions(self)
        self.case_manager_actions = WxCaseManagerActions(self)
        self.case_manager_actions.bind()
        self.workflow = WxCommandWorkflow(
            wx,
            self.command_catalog["commands"],
            self.workflow_plan,
            command_list=self.commands,
            command_details=self.command_details,
            command_filter=self.command_filter,
            add_button=self.add_step,
            flow=self.flow,
            remove_button=self.remove_step,
            move_up_button=self.move_step_up,
            move_down_button=self.move_step_down,
            status=self.status,
        )
        self.release_selection = ReleaseSelectionController(self)
        self.release_selection.bind()
        self.inspector = WxTypedInspector(
            wx,
            key_list=self.key_list,
            editor_panel=self.value_editor_panel,
            editor_sizer=self.value_editor_sizer,
            type_label=self.parameter_type,
            apply_button=self.apply_value,
            status=self.status,
            current_document=self._current_document,
            on_replace=self._inspector_replaced,
        )
        if initial_path:
            self.open_target(str(initial_path), remote=remote, action=action)

    def _drop_target(self):
        page = self

        class CaseDrop(self.wx.FileDropTarget):
            def OnDropFiles(self, _x, _y, filenames):
                paths = [Path(name) for name in filenames]
                target = next((path for path in paths if path.is_dir()), None)
                if target is not None:
                    page.open_target(str(target), remote=False)
                    return True
                if paths:
                    page.open_target(str(paths[0]), remote=False)
                    return True
                return False

        return CaseDrop()

    def open_target(self, path: str, *, remote: bool = False, action=None, read_only: bool = False):
        if action == "new" and not remote:
            self.wx.CallAfter(self.case_manager_actions.create_new_case_at, str(path))
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
                self.wx.CallAfter(self._open_job_draft, None)
        except Exception as exc:
            self._show_error(t("openfoam.case_open_failed").format(error=exc))

    def _open_remote_target(self, path: str, *, action=None, read_only: bool = False):
        session = self.session_state.get("session") or {}
        files = session.get("files") if isinstance(session, dict) else None
        if files is None:
            self._show_error(t("openfoam.remote_unavailable"))
            return
        remote = PurePosixPath(path)
        selected_file = None
        try:
            is_directory = files.is_dir(str(remote))
            if not is_directory:
                selected_file = remote
        except Exception:
            is_directory = False
            selected_file = remote
        case_roots = {"system", "constant", "0", "0.orig"}
        parts = remote.parts
        base_index = next((index for index, part in enumerate(parts) if part in case_roots), None)
        if base_index is not None:
            remote = PurePosixPath(*parts[:base_index])
        elif not is_directory or remote.name in case_roots:
            remote = remote.parent
        self.status.SetLabel(t("openfoam.remote_loading"))

        def worker():
            try:
                workspace, error = CaseWorkspace(
                    str(remote), remote=True, files=files, read_only=read_only
                ), None
            except Exception as exc:
                workspace, error = None, exc
            self.wx.CallAfter(self._remote_loaded, workspace, error, selected_file, action)

        Thread(target=worker, daemon=True).start()

    def _remote_loaded(self, workspace, error, selected_file=None, action=None):
        if error is not None:
            self._show_error(t("openfoam.case_open_failed").format(error=error))
            return
        self._install_workspace(workspace)
        if selected_file is not None:
            self._open_document(str(selected_file))
        if action == "draft":
            self._open_job_draft(None)

    def _install_workspace(self, workspace):
        self.source_tabs.DeleteAllPages()
        self._editors.clear()
        self.workspace = workspace
        self.remote = workspace.remote
        self.documents = workspace.documents
        self.save_actions.workspace_changed(workspace)
        self._populate_tree()
        self._refresh_preview()
        self.save_button.Enable(not workspace.read_only)
        self.undo_button.Enable(not workspace.read_only)
        self.redo_button.Enable(not workspace.read_only)
        self.allrun_button.Enable(not workspace.read_only)
        self.case_manager_actions.refresh_search()
        mode = t("openfoam.remote") if self.remote else t("openfoam.local")
        if workspace.read_only:
            mode = f"{mode} — {t('openfoam.snapshot_read_only')}"
        self.status.SetLabel(t("openfoam.case_opened").format(path=workspace.root, mode=mode))

    def _populate_tree(self):
        self.tree.DeleteAllItems()
        self._tree_paths.clear()
        root_item = self.tree.AddRoot(self.workspace.root if self.workspace else t("openfoam.case_structure"))
        if self.workspace is None:
            return
        nodes = {"": root_item}
        for item in self.workspace.paths:
            clean = item.rstrip("/")
            parent_path = str(PurePosixPath(clean).parent)
            parent_path = "" if parent_path == "." else parent_path
            name = PurePosixPath(clean).name
            parent_item = nodes.get(parent_path, root_item)
            if item.endswith("/"):
                created = self.tree.AppendItem(parent_item, name)
                nodes[clean] = created
            else:
                created = self.tree.AppendItem(parent_item, name)
                self._tree_paths[created.GetID()] = clean
        self.tree.Expand(root_item)

    def _tree_selected(self, event):
        item = event.GetItem()
        relative = self._tree_paths.get(item.GetID())
        if relative:
            self._open_document(relative)
        event.Skip()

    def _open_document(self, target: str):
        if self.workspace is None:
            return
        try:
            document = self.workspace.open_dictionary(target)
        except Exception as exc:
            self._show_error(t("openfoam.dictionary_open_failed").format(error=exc))
            return
        for index, page in enumerate(self._editor_pages()):
            if page[0] == document.relative_path:
                self.source_tabs.SetSelection(index)
                return
        editor = self.wx.TextCtrl(self.source_tabs, value=document.text, style=self.wx.TE_MULTILINE | self.wx.TE_RICH2 | self.wx.HSCROLL)
        editor.SetEditable(not document.read_only)
        self.source_tabs.AddPage(editor, Path(document.relative_path).name, True)
        self._editors[document.relative_path] = editor
        editor.Bind(self.wx.EVT_TEXT, lambda _event, doc=document, control=editor: self._source_changed(doc, control))
        editor.Bind(self.wx.EVT_CHAR_HOOK, self._editor_key)
        self._refresh_inspector(document)
        self._refresh_diff()
        self._refresh_problems()

    def _editor_pages(self):
        result = []
        for index in range(self.source_tabs.GetPageCount()):
            control = self.source_tabs.GetPage(index)
            relative = next((name for name, editor in self._editors.items() if editor is control), "")
            result.append((relative, control))
        return result

    def _current_document(self):
        index = self.source_tabs.GetSelection()
        if index < 0:
            return None
        control = self.source_tabs.GetPage(index)
        return next((doc for doc in self.documents.values() if self._editors.get(doc.relative_path) is control), None)

    def _source_changed(self, document, control):
        if self._loading or (self.workspace is not None and self.workspace.read_only):
            return
        editor_text = control.GetValue().replace("\r\n", "\n").replace("\r", "\n")
        document.set_text(editor_text.replace("\n", preferred_newline(document.decoded.text)))
        for index in range(self.source_tabs.GetPageCount()):
            if self.source_tabs.GetPage(index) is control:
                label = Path(document.relative_path).name + (" *" if document.modified else "")
                self.source_tabs.SetPageText(index, label)
                break
        self._refresh_diff()
        self._refresh_problems()
        self._refresh_inspector(document)

    def _refresh_inspector(self, document=None):
        document = document or self._current_document()
        self.inspector.refresh(document)

    def _inspector_replaced(self, document, _entry, updated):
        if document.read_only:
            return
        editor = self._editors[document.relative_path]
        document.set_text(updated)
        self._loading = True
        try:
            editor.SetValue(updated)
        finally:
            self._loading = False
        self._source_changed(document, editor)

    def _refresh_problems(self, document=None):
        selected = (document,) if document else tuple(self.documents.values())
        values = []
        for item in selected:
            for issue in item.parsed.diagnostics:
                values.append(f"{issue.severity.upper()} {issue.rule_id} {issue.path}:{issue.line}:{issue.column} {issue.message}")
        self.problems.Set(values)

    def _refresh_diff(self):
        lines = []
        for relative, document in self.documents.items():
            if not document.modified:
                continue
            lines.extend(unified_diff(document.decoded.text.splitlines(True), document.text.splitlines(True), fromfile=relative, tofile=relative + " (edited)"))
        self.diff.SetValue("".join(lines) or t("openfoam.no_changes"))

    def _refresh_preview(self):
        if self.workspace is None:
            self.preview.SetValue(t("openfoam.no_case"))
            return
        control = self.documents.get("system/controlDict")
        solver = control.parsed.value("application") if control else None
        solver = solver or t("openfoam.unknown_solver")
        try:
            region_properties = self.workspace.region_properties
            region_summary = (
                t("openfoam.no_regions_declared")
                if region_properties is None
                else region_properties.summary
            )
        except ValueError:
            region_summary = t("openfoam.regions_unresolved")
        self.preview.SetValue(
            f"OpenFOAM.com / ESI\n{self.target_release}\n{t('openfoam.case_root')}: {self.workspace.root}\n"
            f"{t('openfoam.solver')}: {solver}\n{t('openfoam.dictionary_count')}: {len(self.documents)}\n"
            f"{t('openfoam.regions')}: {region_summary}\n"
            f"{t('openfoam.modified_files')}: {len(self.workspace.modified_paths())}\n"
            f"{t('openfoam.runtime_not_run')}"
        )

    def _save(self, _event):
        self.save_actions.save(_event)

    def _recover_save(self, _event):
        self.save_actions.recover(_event)

    def _validate(self, _event):
        if self.workspace is None:
            self.status.SetLabel(t("openfoam.no_case"))
            return
        try:
            from hpc_gui.plugins.linter_tools import load_tool_for_plugin
            from hpc_gui.plugins.loader import load_installed_plugins
            from hpc_gui.plugins.trusted_api3 import api3_linter_entrypoint
            result = load_installed_plugins()
            installed = next(
                (
                    plugin
                    for plugin in result.plugins
                    if getattr(getattr(plugin, "manifest", None), "id", None) == "org.hpcclient.openfoamlint"
                    and getattr(plugin.manifest, "plugin_api", None) == 3
                ),
                None,
            )
            if installed is None:
                self.validation.SetValue(t("openfoam.linter_not_installed"))
                self.bottom.SetSelection(3)
                return
            expected = api3_linter_entrypoint(installed.manifest)
            if expected is None or (installed.linter_engine or {}).get("module") != expected:
                self.validation.SetValue(t("openfoam.linter_not_installed"))
                self.bottom.SetSelection(3)
                return
            tool = load_tool_for_plugin(installed)
            if getattr(tool, "plugin_id", None) != "org.hpcclient.openfoamlint":
                self.validation.SetValue(t("openfoam.linter_not_installed"))
                self.bottom.SetSelection(3)
                return
            import sys as _sys
            module = _sys.modules.get(getattr(tool, "module_name", ""))
            lint_files = getattr(module, "lint_files", None) if module is not None else None
            if not callable(lint_files):
                self.validation.SetValue(t("openfoam.linter_not_installed"))
                self.bottom.SetSelection(3)
                return
            self.validate_button.Disable()
            self.status.SetLabel(t("openfoam.lint_running"))
            contents = {name: document.to_bytes() for name, document in self.documents.items()}
            root = None if self.remote else self.workspace.root

            def worker():
                try:
                    result, error = lint_files(
                        contents, root=root, case_context=True,
                        release=self.target_release,
                    ), None
                except Exception as exc:
                    result, error = None, exc
                self.wx.CallAfter(self._validation_done, result, error)

            Thread(target=worker, daemon=True).start()
        except Exception as exc:
            self._show_error(t("openfoam.validation_failed").format(error=exc))

    def _validation_done(self, result, error):
        self.validate_button.Enable(True)
        if error is not None:
            self._show_error(t("openfoam.validation_failed").format(error=error))
            return
        self.validation.SetValue(result.to_markdown())
        self.bottom.SetSelection(3)
        self.status.SetLabel(t("openfoam.validation_complete").format(
            findings=len(result.diagnostics), level=result.level
        ))

    def _edit_command(self, name):
        if self.workspace is not None and self.workspace.read_only:
            return
        document = self._current_document()
        if document is None:
            return
        changed = document.undo() if name == "Undo" else document.redo()
        if not changed:
            return
        control = self._editors[document.relative_path]
        self._loading = True
        try:
            control.ChangeValue(document.text)
        finally:
            self._loading = False
        self._source_changed(document, control)

    def _editor_key(self, event):
        key = event.GetKeyCode()
        if event.ControlDown() and key in (ord("Z"), ord("z"), ord("Y"), ord("y")):
            redo = key in (ord("Y"), ord("y")) or event.ShiftDown()
            self._edit_command("Redo" if redo else "Undo")
            return
        event.Skip()

    def _open_job_draft(self, _event):
        from .wx_job_draft import open_job_draft

        open_job_draft(self)

    def _create_allrun(self, _event):
        if self.workspace is None:
            self.status.SetLabel(t("openfoam.no_case"))
            return
        if self.workspace.read_only:
            self._show_error(t("openfoam.read_only_allrun"))
            return
        if self.workspace.modified_paths():
            self._show_error(t("openfoam.save_before_allrun"))
            return
        control = self.documents.get("system/controlDict")
        solver = control.parsed.value("application") if control else None
        solver = str(solver or "").strip().strip("\"'")
        try:
            script = render_allrun(solver, self.workflow_plan.steps, self.command_catalog["commands"])
        except ValueError as exc:
            self._show_error(t("openfoam.allrun_create_failed").format(error=exc))
            return
        workspace = self.workspace
        self.allrun_button.Disable()
        self.status.SetLabel(t("openfoam.generating_allrun"))

        def save_script():
            try:
                path, error = workspace.create_allrun(script), None
            except Exception as exc:
                path, error = None, exc
            self.wx.CallAfter(self._allrun_created, workspace, path, error)

        if workspace.remote:
            Thread(target=save_script, daemon=True).start()
        else:
            save_script()

    def _allrun_created(self, workspace, path, error):
        if self.workspace is not workspace:
            return
        self.allrun_button.Enable(not workspace.read_only)
        if error is not None:
            self._show_error(t("openfoam.allrun_create_failed").format(error=error))
            return
        self.status.SetLabel(t("openfoam.allrun_created").format(path=path))

    def _show_error(self, message):
        self.wx.MessageBox(str(message), t("openfoam.title"), self.wx.OK | self.wx.ICON_WARNING, self.panel)


def create_wx_page(parent=None, *, plugin, session_state=None, initial_path=None, remote=False, action=None):
    controller = WxCaseStudioPage(
        parent, plugin=plugin, session_state=session_state,
        initial_path=initial_path, remote=remote, action=action,
    )
    controller.panel._hpc_trusted_tool_controller = controller
    return controller.panel

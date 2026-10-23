"""Host-owned Journal Studio workspace integrated with the wx shell."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from pathlib import PurePosixPath
from threading import Thread

from hpc_gui.core.i18n import t
from hpc_gui.journal_studio.document import JournalDocument
from hpc_gui.services.journal_studio_files import read_local, read_remote
from hpc_gui.wx_journal_studio_editor import JournalEditorPage


PLUGIN_ID = "org.hpcclient.ansysjournalstudio"
REGISTRY_RELATIVE = "data/command_registry.json"
JOURNAL_SUFFIXES = frozenset({".jou", ".scm"})


def _load_registry(plugin) -> dict:
    root = Path(plugin.directory).resolve()
    relative = Path(REGISTRY_RELATIVE)
    target = (root / relative).resolve()
    if root not in target.parents or not target.is_file() or target.is_symlink():
        raise ValueError("Journal Studio command registry is missing or outside the installed package")
    entries = {item.path: item for item in plugin.manifest.files}
    record = entries.get(REGISTRY_RELATIVE)
    data = target.read_bytes()
    if record is None or len(data) != record.size or hashlib.sha256(data).hexdigest() != record.sha256:
        raise ValueError("Journal Studio command registry failed its manifest integrity check")
    value = json.loads(data.decode("utf-8"))
    if value.get("product_id") != "fluent" or value.get("version_id") != "25.2" or not isinstance(value.get("commands"), list):
        raise ValueError("Journal Studio command registry has an unsupported shape")
    for command in value["commands"]:
        if command.get("verification_status") != "unverified" or command.get("mode_scope") != "unknown" or command.get("parameters") != []:
            raise ValueError("Command registry contains unsupported verified parameter metadata")
    return value


class JournalStudioWorkspace:
    def __init__(self, frame, session_state, plugin):
        import wx

        self.wx = wx
        self.frame = frame
        self.session_state = session_state
        self.plugin = plugin
        self.registry = _load_registry(plugin)
        self.main_notebook = session_state.get("_embedded_main_notebook")
        if self.main_notebook is None:
            raise RuntimeError("The wx shell notebook is unavailable")
        self._pages: dict[int, JournalEditorPage] = {}
        self.panel = session_state.get("_journal_studio_panel")
        if self.panel is None or self.panel.IsBeingDeleted():
            self._build_panel()

    def _build_panel(self):
        wx = self.wx
        self.panel = wx.Panel(self.main_notebook)
        root = wx.BoxSizer(wx.VERTICAL)
        toolbar = wx.WrapSizer(wx.HORIZONTAL)
        self.btn_new = wx.Button(self.panel, label=t("journal_studio.new"))
        self.btn_open = wx.Button(self.panel, label=t("journal_studio.open"))
        self.btn_save = wx.Button(self.panel, label=t("journal_studio.save"))
        self.btn_validate = wx.Button(self.panel, label=t("journal_studio.validate"))
        self.btn_insert = wx.Button(self.panel, label=t("journal_studio.insert_command"))
        self.btn_comment = wx.Button(self.panel, label=t("journal_studio.add_comment"))
        self.btn_undo = wx.Button(self.panel, label=t("journal_studio.undo"))
        self.btn_redo = wx.Button(self.panel, label=t("journal_studio.redo"))
        self.btn_slurm = wx.Button(self.panel, label=t("journal_studio.create_slurm_draft"))
        for button in (self.btn_new, self.btn_open, self.btn_save, self.btn_validate, self.btn_insert, self.btn_comment, self.btn_undo, self.btn_redo, self.btn_slurm):
            toolbar.Add(button, 0, wx.ALL, 3)
        root.Add(toolbar, 0, wx.EXPAND | wx.ALL, 3)
        self.documents = wx.Notebook(self.panel)
        root.Add(self.documents, 1, wx.EXPAND | wx.ALL, 4)
        self.panel.SetSizer(root)
        self.panel.SetDropTarget(self._journal_drop_target())
        self.btn_new.Bind(wx.EVT_BUTTON, lambda _event: self.new_journal())
        self.btn_open.Bind(wx.EVT_BUTTON, lambda _event: self.open_dialog())
        self.btn_save.Bind(wx.EVT_BUTTON, lambda _event: self._active_page() and self._active_page().save())
        self.btn_validate.Bind(wx.EVT_BUTTON, lambda _event: self._active_page() and self._active_page().validate())
        self.btn_insert.Bind(wx.EVT_BUTTON, lambda _event: self._active_page() and self._active_page().insert_selected_command())
        self.btn_comment.Bind(wx.EVT_BUTTON, lambda _event: self._active_page() and self._active_page().add_comment())
        self.btn_undo.Bind(wx.EVT_BUTTON, lambda _event: self._active_page() and self._active_page().undo())
        self.btn_redo.Bind(wx.EVT_BUTTON, lambda _event: self._active_page() and self._active_page().redo())
        self.btn_slurm.Bind(wx.EVT_BUTTON, lambda _event: self.create_slurm_draft())
        self.documents.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self._page_changed)
        self.main_notebook.AddPage(self.panel, t("journal_studio.title"), True)
        self.session_state["_journal_studio_panel"] = self.panel
        self.session_state["_journal_studio_controller"] = self

    def _journal_drop_target(self):
        controller = self

        class _JournalDrop(self.wx.FileDropTarget):
            def OnDropFiles(self, _x, _y, filenames):
                paths = [path for path in filenames if Path(path).suffix.casefold() in JOURNAL_SUFFIXES]
                for path in paths:
                    controller.open_document(path, remote=False)
                return bool(paths)

        return _JournalDrop()

    def _show(self):
        index = self._main_page_index()
        if index >= 0:
            self.main_notebook.SetSelection(index)
        self.panel.Show()

    def _main_page_index(self):
        return next((i for i in range(self.main_notebook.GetPageCount()) if self.main_notebook.GetPage(i) is self.panel), -1)

    def _active_page(self):
        index = self.documents.GetSelection()
        return self._pages.get(index)

    def _page_changed(self, event):
        self._refresh_title()
        event.Skip()

    def _refresh_title(self):
        index = self._main_page_index()
        page = self._active_page()
        name = Path(page.document.path).name if page and page.document.path else t("journal_studio.new")
        if index >= 0:
            self.main_notebook.SetPageText(index, f"{t('journal_studio.title')} — {name}")

    def dispatch(self, action: str) -> bool:
        self._show()
        if action == "new":
            return self.new_journal()
        if action == "open_journal":
            return self.open_dialog()
        if action == "settings":
            self.wx.MessageBox(t("journal_studio.settings"), t("journal_studio.title"), self.wx.OK | self.wx.ICON_INFORMATION, self.panel)
            return True
        return action == "open"

    def _remote_available(self) -> bool:
        session = self.session_state.get("session") or {}
        return bool(session.get("files"))

    def _choose_target(self) -> str | None:
        choices = ["Local"]
        if self._remote_available():
            choices.append("Remote")
        dialog = self.wx.SingleChoiceDialog(self.panel, "Choose journal target", t("journal_studio.new"), choices)
        try:
            return choices[dialog.GetSelection()] if dialog.ShowModal() == self.wx.ID_OK else None
        finally:
            dialog.Destroy()

    def _choose_context(self):
        choices = [
            "Solution / TUI", "Solution / Scheme",
            "Meshing / TUI", "Meshing / Scheme",
        ]
        dialog = self.wx.SingleChoiceDialog(
            self.panel, "Fluent 2025 R2 journal context", t("journal_studio.new"), choices
        )
        try:
            if dialog.ShowModal() != self.wx.ID_OK:
                return None
            return ("meshing" if dialog.GetSelection() >= 2 else "solution",
                    "scheme" if dialog.GetSelection() in (1, 3) else "tui")
        finally:
            dialog.Destroy()

    def _template_text(self, mode: str, language: str) -> str:
        name = (
            "fluent-2025r2-scheme.jou.tpl" if language == "scheme" else
            f"fluent-2025r2-{mode}-tui.jou.tpl"
        )
        relative = f"templates/{name}"
        record = next((item for item in self.plugin.manifest.files if item.path == relative), None)
        if record is None:
            raise ValueError("Selected starter template is not declared by the plugin manifest")
        root = Path(self.plugin.directory).resolve()
        path = (root / relative).resolve()
        if root not in path.parents or path.is_symlink():
            raise ValueError("Selected starter template escapes the installed plugin directory")
        data = path.read_bytes()
        if len(data) != record.size or hashlib.sha256(data).hexdigest() != record.sha256:
            raise ValueError("Selected starter template failed its manifest integrity check")
        return data.decode("utf-8")

    def new_journal(self, *, initial_path: str | None = None, remote: bool | None = None) -> bool:
        self._show()
        context = self._choose_context()
        if context is None:
            return False
        mode, language = context
        target = ("Remote" if remote else "Local") if remote is not None else self._choose_target()
        if target is None:
            return False
        if target == "Remote":
            initial = str(PurePosixPath(initial_path or "/") / "untitled.jou") if initial_path else "/untitled.jou"
            dialog = self.wx.TextEntryDialog(self.panel, "Absolute remote .jou path", t("journal_studio.new"), initial)
            try:
                if dialog.ShowModal() != self.wx.ID_OK:
                    return False
                path = dialog.GetValue().strip()
            finally:
                dialog.Destroy()
            if not path or not path.startswith("/") or ".." in PurePosixPath(path).parts:
                self.wx.MessageBox("Enter a safe absolute POSIX path.", t("journal_studio.title"), self.wx.OK | self.wx.ICON_ERROR, self.panel)
                return False
            document = JournalDocument.new(path=path, remote=True, text=self._template_text(mode, language))
        else:
            default_dir = initial_path if initial_path and Path(initial_path).is_dir() else ""
            dialog = self.wx.FileDialog(self.panel, t("journal_studio.new"), defaultDir=default_dir, defaultFile="untitled.jou", wildcard="Journal files (*.jou;*.scm)|*.jou;*.scm|All files (*.*)|*.*", style=self.wx.FD_SAVE)
            try:
                if dialog.ShowModal() != self.wx.ID_OK:
                    return False
                path = dialog.GetPath()
            finally:
                dialog.Destroy()
            if Path(path).exists():
                self.wx.MessageBox("The selected file already exists. Open it or choose a new name.", t("journal_studio.title"), self.wx.OK | self.wx.ICON_WARNING, self.panel)
                return False
            document = JournalDocument.new(path=path, text=self._template_text(mode, language))
        self._add_document(document, mode=mode, language=language)
        return True

    def open_dialog(self) -> bool:
        self._show()
        choices = ["Local"]
        if self._remote_available():
            choices.append("Remote")
        dialog = self.wx.SingleChoiceDialog(self.panel, "Choose journal source", t("journal_studio.open"), choices)
        try:
            target = choices[dialog.GetSelection()] if dialog.ShowModal() == self.wx.ID_OK else None
        finally:
            dialog.Destroy()
        if target is None:
            return False
        if target == "Remote":
            prompt = self.wx.TextEntryDialog(self.panel, "Absolute remote journal path", t("journal_studio.open"), "/")
            try:
                path = prompt.GetValue() if prompt.ShowModal() == self.wx.ID_OK else ""
            finally:
                prompt.Destroy()
            return self.open_document(path, remote=True) if path else False
        dialog = self.wx.FileDialog(self.panel, t("journal_studio.open"), wildcard="Journal files (*.jou;*.scm)|*.jou;*.scm|All files (*.*)|*.*", style=self.wx.FD_OPEN | self.wx.FD_FILE_MUST_EXIST)
        try:
            path = dialog.GetPath() if dialog.ShowModal() == self.wx.ID_OK else ""
        finally:
            dialog.Destroy()
        return self.open_document(path, remote=False) if path else False

    def create_slurm_draft(self) -> bool:
        self._show()
        page = self._active_page()
        if page is None:
            self.wx.MessageBox(t("journal_studio.slurm_no_document"), t("journal_studio.title"), self.wx.OK | self.wx.ICON_INFORMATION, self.panel)
            return False
        document = page.document
        if not document.path or document.modified:
            self.wx.MessageBox(t("journal_studio.slurm_unsaved"), t("journal_studio.title"), self.wx.OK | self.wx.ICON_WARNING, self.panel)
            return False
        from hpc_gui.wx_journal_slurm_draft_dialog import SlurmDraftDialog, open_draft_in_editor

        session = self.session_state.get("session") or {}
        dialog = SlurmDraftDialog(
            self.panel, document, session.get("profile"),
            lambda script_path, script_text: open_draft_in_editor(self.session_state, script_path, script_text),
        )
        dialog.show_modal()
        return True

    def open_document(self, path: str, *, remote: bool, validate: bool = False) -> bool:
        self._show()
        identity = (remote, path)
        for index, page in self._pages.items():
            if (page.document.remote, page.document.path) == identity:
                self.documents.SetSelection(index)
                if validate:
                    self.wx.CallAfter(page.validate)
                return True
        session = self.session_state.get("session") or {}
        files_backend = session.get("files") if remote else None
        if remote and files_backend is None:
            self.wx.MessageBox(t("journal_studio.remote_unavailable"), t("journal_studio.title"), self.wx.OK | self.wx.ICON_WARNING, self.panel)
            return False
        self.status_message(f"Opening {path}…")

        def worker():
            try:
                data = read_remote(files_backend, path) if remote else read_local(path)
                document = JournalDocument.from_bytes(data, path=path, remote=remote)
                self.wx.CallAfter(self._open_done, document, None, validate)
            except Exception as exc:
                self.wx.CallAfter(self._open_done, None, str(exc), False)

        Thread(target=worker, daemon=True).start()
        return True

    def _open_done(self, document, error, validate):
        if error:
            self.status_message(error)
            return
        self._add_document(document)
        if validate:
            self.wx.CallAfter(self._active_page().validate)

    def _add_document(self, document: JournalDocument, *, mode="solution", language="tui"):
        page = JournalEditorPage(
            self.documents, document, session_state=self.session_state,
            registry=self.registry, mode=mode, language=language,
        )
        title = Path(document.path).name if document.path else t("journal_studio.new")
        self.documents.AddPage(page.page, title, True)
        self._pages[self.documents.GetPageCount() - 1] = page
        self.session_state["_journal_studio_controller"] = self
        self._refresh_title()
        self.status_message("")

    def status_message(self, message: str):
        try:
            self.frame.SetStatusText(message)
        except Exception:
            if message:
                self.wx.LogMessage(message)


def _controller(frame, session_state, plugin):
    current = session_state.get("_journal_studio_controller")
    if current is not None and current.plugin.manifest.id == plugin.manifest.id:
        return current
    current = JournalStudioWorkspace(frame, session_state, plugin)
    session_state["_journal_studio_controller"] = current
    return current


def dispatch_journal_studio_action(frame, session_state, plugin, action: str) -> bool:
    return _controller(frame, session_state, plugin).dispatch(action)


def open_journal_from_context(frame, session_state, plugin, path: str, *, remote: bool, validate: bool = False) -> bool:
    return _controller(frame, session_state, plugin).open_document(path, remote=remote, validate=validate)

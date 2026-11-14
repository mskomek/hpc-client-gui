"""Multi-document tab creation and lifecycle for the wx editor."""

from __future__ import annotations

from hpc_gui.services.editor_controller import DocumentModel, detect_newline
from hpc_gui.services.editor_controller import EditorCommandService
from hpc_gui.wx_editor_file_safety import editor_binary_guard_reason


def create_document_notebook(panel, root, model, wx, translate):
    """Create the movable, closable notebook and its initial document pages."""
    try:
        from wx.lib.agw import aui

        tabs = aui.AuiNotebook(
            panel,
            style=aui.AUI_NB_DEFAULT_STYLE | aui.AUI_NB_CLOSE_ON_ALL_TABS,
        )
    except (ImportError, AttributeError):
        aui = None
        tabs = wx.Notebook(panel)
    for doc in model.controller.documents:
        page = wx.Panel(tabs)
        tabs.AddPage(page, tab_label(doc, translate))
    try:
        active = model.controller.active_index
        tabs.SetSelection(active if 0 <= active < tabs.GetPageCount() else 0)
    except Exception:
        pass
    if tabs.GetPageCount() == 0:
        page = wx.Panel(tabs)
        doc = model.controller.active
        tabs.AddPage(page, tab_label(doc, translate) if doc else translate("editor.title"))
        try:
            tabs.SetSelection(0)
        except Exception:
            pass
    root.Add(tabs, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 4)
    return tabs, aui


def tab_label(doc, translate):
    base = doc.path.rsplit("/", 1)[-1] if doc.path else translate("editor.title")
    return f"{base} *" if getattr(doc, "dirty", False) else base


class WxEditorTabs:
    """Own document identity, notebook state, loading, ordering, and closure."""

    def __init__(
        self, *, panel, wx, aui, tabs, model, editor, remote_path, host, state,
        status, translate, note_disk_baseline, update_header_enabled, save_document,
    ):
        self.panel = panel
        self.wx = wx
        self.aui = aui
        self.tabs = tabs
        self.model = model
        self.editor = editor
        self.remote_path = remote_path
        self.host = host
        self.state = state
        self.status = status
        self.t = translate
        self.note_disk_baseline = note_disk_baseline
        self.update_header_enabled = update_header_enabled
        self.save_document = save_document
        self.editor.Bind(wx.EVT_TEXT, self.content_changed)
        try:
            tabs.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.on_tab_changed)
        except Exception:
            pass
        if aui is not None:
            try:
                tabs.Bind(aui.EVT_AUINOTEBOOK_PAGE_CHANGED, self.on_tab_changed)
                tabs.Bind(aui.EVT_AUINOTEBOOK_PAGE_CLOSE, self._on_tab_close)
            except Exception:
                pass

    def refresh(self):
        try:
            while self.tabs.GetPageCount() < len(self.model.controller.documents):
                self.tabs.AddPage(self.wx.Panel(self.tabs), "")
            while self.tabs.GetPageCount() > len(self.model.controller.documents):
                self.tabs.DeletePage(self.tabs.GetPageCount() - 1)
            for idx, doc in enumerate(self.model.controller.documents):
                if idx < self.tabs.GetPageCount():
                    self.tabs.SetPageText(idx, tab_label(doc, self.t))
            active = self.model.controller.active_index
            if self.tabs.GetPageCount():
                self.tabs.SetSelection(active if 0 <= active < self.tabs.GetPageCount() else 0)
        except Exception:
            pass

    def on_tab_changed(self, event):
        idx = event.GetSelection()
        if 0 <= idx < len(self.model.controller.documents):
            try:
                self.model.controller.active_index = idx
                doc = self.model.controller.active
                if doc is not None:
                    self.editor.ChangeValue(doc.content)
                    self.remote_path.SetValue(doc.path)
                    self.host.set_host_title(
                        EditorCommandService.suggested_filename(doc.path or "untitled.sh")
                    )
            except Exception:
                pass
        event.Skip()

    def update_dirty_marker(self):
        try:
            idx = self.model.controller.active_index
            if 0 <= idx < self.tabs.GetPageCount() and idx < len(self.model.controller.documents):
                self.tabs.SetPageText(idx, tab_label(self.model.controller.documents[idx], self.t))
        except Exception:
            pass

    def content_changed(self, event):
        if not self.state["in_flight"]:
            self.model.controller.update_content(self.editor.GetValue())
            self.update_dirty_marker()
        event.Skip()

    def reorder(self, from_idx: int, to_idx: int):
        try:
            docs = list(self.model.controller.documents)
            if 0 <= from_idx < len(docs) and 0 <= to_idx < len(docs):
                docs.insert(to_idx, docs.pop(from_idx))
                self.model.controller.documents = docs
                active = self.model.controller.active_index
                if active == from_idx:
                    self.model.controller.active_index = to_idx
                elif from_idx < active <= to_idx:
                    self.model.controller.active_index -= 1
                elif to_idx <= active < from_idx:
                    self.model.controller.active_index += 1
                self.refresh()
                return True
        except Exception:
            pass
        return False

    def begin_open_request(self) -> int:
        try:
            self.state["open_seq"] = int(self.state.get("open_seq", 0)) + 1
            return int(self.state["open_seq"])
        except Exception:
            return 0

    def load_document(
        self, new_path, new_content, *, is_local=False, provider: str = "",
        profile: str = "", session_key: str = "", encoding: str = "utf-8",
        newline: str | None = None, version: str = "", request_seq: int | None = None,
    ):
        if request_seq is None:
            request_seq = self.begin_open_request()
        try:
            if int(request_seq) < int(self.state.get("open_seq", 0)):
                self._set_status("editor.stale_open_ignored", "Ignored a stale editor-open request.")
                return "stale-ignored"
            self.state["open_applied"] = int(request_seq)
        except Exception:
            pass
        guard = editor_binary_guard_reason(new_path, new_content)
        if guard:
            self._set_status(guard)
            return "refused-binary"
        newline_style = newline if newline in ("\n", "\r\n") else detect_newline(new_content)
        probe = DocumentModel(
            new_path, new_content, new_content, is_local, encoding,
            suggested_filename=EditorCommandService.suggested_filename(new_path),
            provider=provider, profile=profile, session_key=session_key,
            newline=newline_style, version=version,
        )
        for idx, doc in enumerate(self.model.controller.documents):
            if doc.canonical_key == probe.canonical_key and probe.canonical_key[4]:
                self.model.controller.active_index = idx
                self.editor.ChangeValue(doc.content)
                self.remote_path.SetValue(doc.path)
                self.host.set_host_title(EditorCommandService.suggested_filename(doc.path or "untitled.sh"))
                self.note_disk_baseline(doc)
                self.refresh()
                return "activated"
        self.model.controller.open(probe)
        self.note_disk_baseline(probe)
        self.editor.ChangeValue(new_content)
        self.state["binary_refused"] = False
        self.editor.SetEditable(True)
        self.remote_path.SetValue(new_path)
        self.host.set_host_title(EditorCommandService.suggested_filename(new_path or "untitled.sh"))
        self.update_header_enabled()
        self.refresh()
        return "opened"

    def _set_status(self, message):
        try:
            self.status.SetLabel(message)
        except Exception:
            pass

    def remove(self, idx: int) -> bool:
        try:
            docs = list(self.model.controller.documents)
            docs.pop(idx)
            self.model.controller.documents = docs
            if self.model.controller.active_index >= len(docs):
                self.model.controller.active_index = max(0, len(docs) - 1)
            elif self.model.controller.active_index > idx:
                self.model.controller.active_index -= 1
            self.refresh()
            active = self.model.controller.active
            if active is not None:
                self.editor.ChangeValue(active.content)
                self.remote_path.SetValue(active.path)
                self.host.set_host_title(EditorCommandService.suggested_filename(active.path or "untitled.sh"))
            else:
                self.editor.Clear()
            return True
        except Exception:
            return False

    def close(self, index: int | None = None, *, force: bool = False) -> bool:
        if self.state["in_flight"] or (len(self.model.controller.documents) <= 1 and not force):
            return False
        idx = int(index) if index is not None else int(self.model.controller.active_index)
        if not (0 <= idx < len(self.model.controller.documents)):
            return False
        doc = self.model.controller.documents[idx]
        if doc.dirty and not force:
            choice = self.wx.MessageBox(
                self.t("common.save_changes"), self.t("tabs.editor"),
                self.wx.YES_NO | self.wx.CANCEL | self.wx.ICON_WARNING,
            )
            if choice == self.wx.CANCEL:
                return False
            if choice == self.wx.YES:
                if self.state.get("binary_refused"):
                    return False
                self.model.controller.active_index = idx
                self.editor.ChangeValue(doc.content)
                self.remote_path.SetValue(doc.path)
                self.tabs.Disable()

                def finish_close():
                    self.tabs.Enable(True)
                    self.remove(idx)

                def keep_open(_error):
                    self.tabs.Enable(True)

                started = self.save_document(
                    on_done=finish_close, on_error=keep_open, require_saved=True,
                )
                if not started:
                    self.tabs.Enable(True)
                    return False
                return True
        return self.remove(idx)

    def _on_tab_close(self, event):
        index = event.GetSelection()
        event.Veto()
        self.close(index)

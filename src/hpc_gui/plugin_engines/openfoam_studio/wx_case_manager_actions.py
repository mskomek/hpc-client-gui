"""Case search and snapshot actions for the wx Case Studio page."""
from __future__ import annotations

from pathlib import Path

from hpc_gui.core.i18n import t


def valid_case_folder_name(name: str) -> bool:
    """Accept one plain directory name on both Windows and POSIX."""
    clean = str(name).strip()
    return bool(clean) and clean not in {".", ".."} and not any(
        character in clean for character in ("/", "\\", "\0")
    ) and Path(clean).name == clean


class WxCaseManagerActions:
    def __init__(self, page):
        self.page = page
        self.hits = ()

    def bind(self):
        wx = self.page.wx
        self.page.case_search.Bind(wx.EVT_TEXT, self._search)
        self.page.case_search_results.Bind(wx.EVT_LISTBOX, self._open_hit)
        self.page.new_button.Bind(wx.EVT_BUTTON, self._new_case)
        self.page.open_button.Bind(wx.EVT_BUTTON, self._open_case)
        self.page.snapshot_button.Bind(wx.EVT_BUTTON, self._open_snapshot)

    def refresh_search(self):
        query = self.page.case_search.GetValue()
        self._set_hits(query)

    def _search(self, event):
        self._set_hits(self.page.case_search.GetValue())
        event.Skip()

    def _set_hits(self, query):
        workspace = self.page.workspace
        self.hits = () if workspace is None else workspace.search(query)
        self.page.case_search_results.Set([
            f"{hit.relative_path}:{hit.line}:{hit.column}  {hit.text.strip()}"
            for hit in self.hits
        ])

    def _open_hit(self, event):
        index = self.page.case_search_results.GetSelection()
        if not 0 <= index < len(self.hits):
            return
        hit = self.hits[index]
        self.page._open_document(hit.relative_path)
        editor = self.page._editors.get(hit.relative_path)
        if editor is not None:
            content = editor.GetValue()
            lines = content.splitlines(keepends=True)
            line_start = sum(len(line) for line in lines[: hit.line - 1])
            position = min(line_start + hit.column - 1, len(content))
            editor.SetInsertionPoint(position)
            editor.ShowPosition(position)
            editor.SetFocus()
        event.Skip()


    def _new_case(self, _event):
        page = self.page
        wx = page.wx
        choose = wx.DirDialog(
            page.panel, t("openfoam.choose_parent"),
            style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST,
        )
        try:
            if choose.ShowModal() != wx.ID_OK:
                return
            parent = Path(choose.GetPath())
        finally:
            choose.Destroy()
        self.create_new_case_at(parent)

    def create_new_case_at(self, parent: str | Path):
        page = self.page
        wx = page.wx
        dialog = wx.TextEntryDialog(
            page.panel, t("openfoam.case_name_prompt"), t("openfoam.new_case"), "OpenFOAMCase"
        )
        try:
            if dialog.ShowModal() != wx.ID_OK:
                return
            name = dialog.GetValue().strip()
        finally:
            dialog.Destroy()
        if not valid_case_folder_name(name):
            page._show_error(t("openfoam.invalid_case_name"))
            return
        target = Path(parent).expanduser() / name
        try:
            target.parent.resolve(strict=True)
            target.mkdir()
            for folder in ("system", "constant", "0"):
                (target / folder).mkdir()
            (target / "README-openfoam-starter.txt").write_text(
                t("openfoam.starter_readme") + "\n", encoding="utf-8"
            )
            page.open_target(str(target))
        except FileExistsError:
            page._show_error(t("openfoam.case_exists"))
        except OSError as exc:
            page._show_error(t("openfoam.case_create_failed").format(error=exc))

    def _open_case(self, _event):
        page = self.page
        wx = page.wx
        choices = [t("openfoam.local")]
        session = page.session_state.get("session") or {}
        if isinstance(session, dict) and session.get("files"):
            choices.append(t("openfoam.remote"))
        dialog = wx.SingleChoiceDialog(
            page.panel, t("openfoam.choose_case_mode"), t("openfoam.open_case"), choices
        )
        try:
            if dialog.ShowModal() != wx.ID_OK:
                return
            remote = dialog.GetSelection() == 1
        finally:
            dialog.Destroy()
        if remote:
            prompt = wx.TextEntryDialog(
                page.panel, t("openfoam.remote_case_path"), t("openfoam.open_case"), "/"
            )
            try:
                if prompt.ShowModal() == wx.ID_OK:
                    page.open_target(prompt.GetValue().strip(), remote=True)
            finally:
                prompt.Destroy()
            return
        choose = wx.DirDialog(
            page.panel, t("openfoam.open_case"),
            style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST,
        )
        try:
            if choose.ShowModal() == wx.ID_OK:
                page.open_target(choose.GetPath())
        finally:
            choose.Destroy()

    def _open_snapshot(self, _event):
        page = self.page
        wx = page.wx
        choices = [t("openfoam.local")]
        session = page.session_state.get("session") or {}
        if isinstance(session, dict) and session.get("files"):
            choices.append(t("openfoam.remote"))
        dialog = wx.SingleChoiceDialog(
            page.panel, t("openfoam.snapshot_mode"), t("openfoam.open_snapshot"), choices
        )
        try:
            if dialog.ShowModal() != wx.ID_OK:
                return
            remote = dialog.GetSelection() == 1
        finally:
            dialog.Destroy()
        if remote:
            prompt = wx.TextEntryDialog(
                page.panel, t("openfoam.remote_case_path"), t("openfoam.open_snapshot"), "/"
            )
            try:
                if prompt.ShowModal() == wx.ID_OK:
                    page.open_target(prompt.GetValue().strip(), remote=True, read_only=True)
            finally:
                prompt.Destroy()
            return
        choose = wx.DirDialog(
            page.panel, t("openfoam.open_snapshot"),
            style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST,
        )
        try:
            if choose.ShowModal() == wx.ID_OK:
                page.open_target(choose.GetPath(), read_only=True)
        finally:
            choose.Destroy()

"""wx-native standalone linter page; all validation is read-only and runs off the UI thread."""
from __future__ import annotations

from threading import Event, Thread
from pathlib import Path

from hpc_gui.core.i18n import t
from hpc_gui.openfoam_core import DecodedSource
from hpc_gui.openfoam_core.cancellation import ScanCancelledError
from hpc_gui.openfoam_core.files import read_dictionary_file
from hpc_gui.openfoam_core.release_support import supported_releases

from .api import lint_paths, rule_catalog


class WxLinterPage:
    def __init__(self, parent, *, initial_paths=(), session_state=None, remote=False, auto_run=False):
        import wx

        self.wx = wx
        self.page = wx.Panel(parent)
        self.session_state = session_state or {}
        self.target_release = "v2312"
        self.paths = [str(path) for path in initial_paths]
        self.remote = bool(remote)
        self.result = None
        self.findings = []
        self._cancel_event = None
        self._stale_snapshot = {}
        self._stale = False
        self._build()
        if auto_run and self.paths:
            wx.CallAfter(self._run_lint, None)

    def _build(self):
        wx = self.wx
        outer = wx.BoxSizer(wx.VERTICAL)
        header = wx.WrapSizer(wx.HORIZONTAL)
        title = wx.StaticText(self.page, label=t("openfoam.linter_title"))
        title.SetFont(title.GetFont().Bold())
        header.Add(title, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        header.Add(wx.StaticText(self.page, label=t("openfoam.edition")), 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 14)
        self.edition = wx.Choice(self.page, choices=["OpenFOAM.com / ESI"])
        self.edition.SetSelection(0)
        self.edition.Enable(False)
        header.Add(self.edition, 0, wx.ALL, 4)
        self.version = wx.Choice(self.page, choices=list(supported_releases()))
        self.version.SetSelection(0)
        self.version.Enable(True)
        header.Add(self.version, 0, wx.ALL, 4)
        self.add_file = wx.Button(self.page, label=t("openfoam.add_file"))
        self.add_case = wx.Button(self.page, label=t("openfoam.add_case"))
        self.run = wx.Button(self.page, label=t("openfoam.validate"))
        self.cancel = wx.Button(self.page, label=t("openfoam.cancel"))
        self.cancel.Disable()
        self.export = wx.Button(self.page, label=t("openfoam.export_json"))
        for control in (self.add_file, self.add_case, self.run, self.cancel, self.export):
            header.Add(control, 0, wx.ALL, 3)
        outer.Add(header, 0, wx.EXPAND)
        self.status = wx.StaticText(self.page, label=t("openfoam.static_only"))
        outer.Add(self.status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)

        self.tabs = wx.Notebook(self.page)
        self.files = wx.ListBox(self.tabs)
        self.rules = wx.ListBox(self.tabs)
        self.diagnostics = wx.ListCtrl(self.tabs, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.diagnostics.InsertColumn(0, t("openfoam.severity"), width=90)
        self.diagnostics.InsertColumn(1, t("openfoam.verification"), width=110)
        self.diagnostics.InsertColumn(2, t("openfoam.rule"), width=120)
        self.diagnostics.InsertColumn(3, t("openfoam.location"), width=260)
        self.diagnostics.InsertColumn(4, t("openfoam.finding"), width=520)
        self.details = wx.TextCtrl(self.tabs, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
        self.tabs.AddPage(self.files, t("openfoam.files"))
        self.tabs.AddPage(self.rules, t("openfoam.rules"))
        self.tabs.AddPage(self.diagnostics, t("openfoam.diagnostics"))
        self.tabs.AddPage(self.details, t("openfoam.details"))
        outer.Add(self.tabs, 1, wx.EXPAND | wx.ALL, 5)
        self.page.SetSizer(outer)

        for rule_id, metadata in sorted(rule_catalog().items()):
            self.rules.Append(f"{rule_id}  [{metadata.get('verification_level', 'static')} / {metadata.get('severity', 'info')}]  {metadata.get('title', '')}")
        self._refresh_files()
        self.add_file.Bind(wx.EVT_BUTTON, self._choose_file)
        self.add_case.Bind(wx.EVT_BUTTON, self._choose_case)
        self.run.Bind(wx.EVT_BUTTON, self._run_lint)
        self.export.Bind(wx.EVT_BUTTON, self._export_json)
        self.cancel.Bind(wx.EVT_BUTTON, self._cancel_lint)
        self.version.Bind(wx.EVT_CHOICE, self._release_changed)
        self.diagnostics.Bind(wx.EVT_LIST_ITEM_SELECTED, self._show_details)
        self.diagnostics.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self._open_source)
        self._stale_timer = wx.Timer(self.page)
        self.page.Bind(wx.EVT_TIMER, self._check_stale, self._stale_timer)
        if self.remote:
            self.add_file.Disable()
            self.add_case.Disable()

    def _refresh_files(self):
        self.files.Set([str(path) for path in self.paths])

    def _release_changed(self, _event):
        self.target_release = self.version.GetStringSelection()
        if self.result is not None:
            self._mark_existing_results_stale()
        else:
            self.status.SetLabel(
                f"OpenFOAM.com / ESI {self.target_release}; static common-rule profile."
            )

    def open_paths(self, paths, *, remote=False, action=None):
        self.paths = [str(path) for path in paths]
        self.remote = bool(remote)
        self._refresh_files()
        if action == "validate" and self.paths:
            self.wx.CallAfter(self._run_lint, None)

    def _choose_file(self, _event):
        dialog = self.wx.FileDialog(self.page, t("openfoam.add_file"), wildcard=t("openfoam.dictionary_filter"), style=self.wx.FD_OPEN | self.wx.FD_MULTIPLE | self.wx.FD_FILE_MUST_EXIST)
        try:
            if dialog.ShowModal() == self.wx.ID_OK:
                self.paths.extend(path for path in dialog.GetPaths() if path not in self.paths)
                self._refresh_files()
                self._mark_existing_results_stale()
        finally:
            dialog.Destroy()

    def _choose_case(self, _event):
        dialog = self.wx.DirDialog(self.page, t("openfoam.add_case"), style=self.wx.DD_DEFAULT_STYLE | self.wx.DD_DIR_MUST_EXIST)
        try:
            if dialog.ShowModal() == self.wx.ID_OK and dialog.GetPath() not in self.paths:
                self.paths.append(dialog.GetPath())
                self._refresh_files()
                self._mark_existing_results_stale()
        finally:
            dialog.Destroy()

    def _run_lint(self, _event):
        if not self.paths:
            self.status.SetLabel(t("openfoam.select_path"))
            return
        self.run.Disable()
        self.version.Disable()
        self.add_file.Disable()
        self.add_case.Disable()
        self.export.Disable()
        self.cancel.Enable()
        self.status.SetLabel(t("openfoam.lint_running"))
        chosen = tuple(self.paths)
        release = self.version.GetStringSelection()
        self.target_release = release
        event = Event()
        self._cancel_event = event
        self._stale = False
        self._stale_snapshot = {}
        self._stale_timer.Stop()

        def worker():
            cancelled = False
            try:
                if self.remote:
                    from .remote_case import lint_remote_path

                    session = self.session_state.get("session") or {}
                    files = session.get("files") if isinstance(session, dict) else getattr(session, "files", None)
                    if files is None or len(chosen) != 1:
                        raise RuntimeError("a connected SFTP session and one remote case path are required")
                    result = lint_remote_path(
                        chosen[0], files, cancel_event=event, release=release,
                    )
                else:
                    result = lint_paths(
                        chosen, cancel_event=event, release=release,
                    )
                error = None
            except ScanCancelledError:
                result, error, cancelled = None, None, True
            except Exception as exc:
                result, error = None, exc
            self.wx.CallAfter(self._lint_done, result, error, cancelled)

        Thread(target=worker, daemon=True).start()

    def _cancel_lint(self, _event):
        if self._cancel_event is not None:
            self._cancel_event.set()
            self.cancel.Disable()
            self.status.SetLabel(t("openfoam.cancel_requested"))

    def _lint_done(self, result, error, cancelled=False):
        self.run.Enable(True)
        self.version.Enable(True)
        self.cancel.Disable()
        if not self.remote:
            self.add_file.Enable(True)
            self.add_case.Enable(True)
        self.export.Enable(bool(self.result is not None and not self._stale))
        self._cancel_event = None
        if cancelled:
            self.status.SetLabel(t("openfoam.cancelled"))
            return
        if error is not None:
            self.status.SetLabel(t("openfoam.lint_failed").format(error=error))
            return
        self.result = result
        self.findings = list(result.diagnostics)
        self.diagnostics.DeleteAllItems()
        for finding in self.findings:
            index = self.diagnostics.InsertItem(self.diagnostics.GetItemCount(), finding.severity)
            self.diagnostics.SetItem(index, 1, finding.verification_level)
            self.diagnostics.SetItem(index, 2, finding.rule_id)
            self.diagnostics.SetItem(index, 3, f"{finding.path}:{finding.line}:{finding.column}")
            self.diagnostics.SetItem(index, 4, finding.message)
        self.status.SetLabel(
            f"OpenFOAM.com / ESI {result.version}; "
            + t("openfoam.lint_summary").format(
                files=len(result.files_checked), errors=result.errors,
                warnings=result.warnings,
            )
        )
        if not self.findings:
            self.details.SetValue(t("openfoam.no_findings"))
        self.tabs.SetSelection(2)
        self._stale_snapshot = self._snapshot_result_files(result.files_checked)
        if self._stale_snapshot and not self.remote:
            self._stale_timer.Start(1000)
        self.export.Enable(True)

    @staticmethod
    def _snapshot_result_files(paths):
        snapshot = {}
        for raw in paths:
            path = Path(raw)
            try:
                if path.is_file() and not path.is_symlink():
                    info = path.stat()
                    snapshot[str(path)] = (info.st_size, info.st_mtime_ns)
            except OSError:
                snapshot[str(path)] = None
        return snapshot

    def _check_stale(self, _event):
        if self._stale or not self._stale_snapshot:
            self._stale_timer.Stop()
            return
        if self._snapshot_result_files(self._stale_snapshot) != self._stale_snapshot:
            self._stale = True
            self._stale_timer.Stop()
            self.export.Disable()
            self.status.SetLabel(t("openfoam.results_stale"))

    def _mark_existing_results_stale(self):
        if self.result is not None:
            self._stale = True
            self._stale_timer.Stop()
            self.export.Disable()
            self.status.SetLabel(t("openfoam.results_stale"))

    def _show_details(self, event):
        index = event.GetIndex()
        if 0 <= index < len(self.findings):
            finding = self.findings[index]
            self.details.SetValue(
                f"{finding.rule_id} — {finding.severity}\n"
                f"{finding.path}:{finding.line}:{finding.column}\n\n"
                f"{finding.message}\n\n{finding.suggested_fix}\n\n"
                f"Confidence: {finding.confidence}\nLevel: {finding.verification_level}\n"
                f"Source: {finding.source_url}"
            )
            self.tabs.SetSelection(3)

    def _open_source(self, event):
        index = event.GetIndex()
        if not 0 <= index < len(self.findings):
            return
        finding = self.findings[index]
        manager = self.session_state.get("editor_manager")
        if manager is None:
            self.status.SetLabel(t("openfoam.source_open_failed").format(path=finding.path))
            return
        path = finding.path
        if not self.remote and not Path(path).is_absolute():
            for root in self.paths:
                parent = Path(root)
                candidate = parent / Path(*Path(path).parts)
                if candidate.is_file():
                    path = str(candidate)
                    break
        try:
            if self.remote:
                from .remote_case import read_remote_dictionary_text

                session = self.session_state.get("session") or {}
                files = session.get("files") if isinstance(session, dict) else getattr(session, "files", None)
                if files is None:
                    raise RuntimeError("authenticated SFTP session is unavailable")
                text = read_remote_dictionary_text(path, files)
                frame = manager.open_primary(path, text, is_local=False)
            else:
                target = read_dictionary_file(path)
                text = DecodedSource.from_bytes(target.data).text
                frame = manager.open_primary(path, text, is_local=True)
            controls = getattr(frame, "_wx_editor_controls", {})
            editor = controls.get("editor") if isinstance(controls, dict) else None
            if editor is not None:
                position = editor.PositionFromLine(max(0, int(finding.line) - 1))
                if position >= 0:
                    editor.SetInsertionPoint(position)
                    editor.ShowPosition(position)
                    editor.SetFocus()
        except (OSError, UnicodeError, ValueError, RuntimeError) as exc:
            self.details.SetValue(t("openfoam.source_open_failed").format(path=f"{path} ({exc})"))

    def _export_json(self, _event):
        if self.result is None:
            self.status.SetLabel(t("openfoam.run_before_export"))
            return
        if self._stale:
            self.status.SetLabel(t("openfoam.results_stale"))
            return
        dialog = self.wx.FileDialog(self.page, t("openfoam.export_json"), defaultFile="openfoam-lint.json", wildcard="JSON (*.json)|*.json", style=self.wx.FD_SAVE | self.wx.FD_OVERWRITE_PROMPT)
        try:
            if dialog.ShowModal() == self.wx.ID_OK:
                Path(dialog.GetPath()).write_text(self.result.to_json(), encoding="utf-8")
                self.status.SetLabel(t("openfoam.report_saved"))
        finally:
            dialog.Destroy()


def create_wx_page(parent=None, *, initial_paths=(), session_state=None, remote=False, auto_run=False):
    controller = WxLinterPage(
        parent, initial_paths=initial_paths, session_state=session_state,
        remote=remote, auto_run=auto_run,
    )
    controller.page._hpc_trusted_tool_controller = controller
    return controller.page

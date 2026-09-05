"""Real wx ANSYS Trusted Tool surface wired to the framework-neutral engine."""

from __future__ import annotations

from pathlib import Path
from threading import Thread

from hpc_gui.core.i18n import subscribe_language_change, t, unsubscribe_language_change
from hpc_gui.plugins.linter_tools import ToolLoadError, first_linter_tool
from hpc_gui.services.ansys_tool_presentation import AnsysToolPresentation
from hpc_gui.services.help_catalog import is_allowed_external_url
from hpc_gui.wx_ansys import FileDiagnostics, WxAnsysModel


_ALLOWED_DOC_DOMAINS = frozenset({"ansys.com", "docs.ansys.com", "ansyshelp.ansys.com"})


def _tr(key: str, fallback: str) -> str:
    val = t(key)
    return fallback if val.startswith("[") else val


def _severity_of(diag) -> str:
    sev = getattr(getattr(diag, "severity", None), "value", None)
    if isinstance(sev, str):
        return sev.lower()
    raw = getattr(diag, "severity", "")
    return str(raw).lower() if raw else "info"


def _format_location(diag) -> str:
    line = getattr(diag, "line", None)
    col = getattr(diag, "column", None)
    if line is None:
        return "?"
    return f"{line}:{col or 1}"


def build_ansys_frame(parent=None, presentation: AnsysToolPresentation | None = None, *, lifecycle=None):
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc

    if presentation is None:
        try:
            tool = first_linter_tool()
            presentation = AnsysToolPresentation(tool)
        except ToolLoadError as exc:
            frame = wx.Frame(parent, title=t("ansyslint.title"), size=(900, 600))
            panel = wx.Panel(frame)
            sizer = wx.BoxSizer(wx.VERTICAL)
            msg = wx.StaticText(panel, label=str(exc))
            msg.Wrap(880)
            sizer.Add(msg, 1, wx.EXPAND | wx.ALL, 12)
            close_btn = wx.Button(panel, label=t("common.close"))
            close_btn.Bind(wx.EVT_BUTTON, lambda _e: frame.Close())
            sizer.Add(close_btn, 0, wx.ALIGN_RIGHT | wx.ALL, 8)
            panel.SetSizer(sizer)
            frame.Show()
            return frame

    model = WxAnsysModel(presentation)
    frame = wx.Frame(parent, title=f"{t('ansyslint.title')} — {presentation.tool.title}", size=(1000, 700))
    panel = wx.Panel(frame)
    root = wx.BoxSizer(wx.VERTICAL)

    # Toolbar: file / folder pick + lint
    toolbar = wx.BoxSizer(wx.HORIZONTAL)
    pick_files_btn = wx.Button(panel, label="Pick Files")
    pick_folder_btn = wx.Button(panel, label="Pick Folder")
    lint_btn = wx.Button(panel, label="Lint")
    clear_btn = wx.Button(panel, label=t("common.close") if False else "Clear")
    # Use translated labels where available; fallback to English
    toolbar.Add(pick_files_btn, 0, wx.RIGHT, 6)
    toolbar.Add(pick_folder_btn, 0, wx.RIGHT, 6)
    toolbar.Add(lint_btn, 0, wx.RIGHT, 6)
    toolbar.AddStretchSpacer(1)
    toolbar.Add(clear_btn, 0, wx.LEFT, 6)
    root.Add(toolbar, 0, wx.EXPAND | wx.ALL, 8)

    # Status / summary
    _summary_tpl = _tr("ansyslint.summary_label", "{e} error(s), {w} warning(s), {i} info")
    summary_label = wx.StaticText(panel, label=_summary_tpl.replace("{e}", "0").replace("{w}", "0").replace("{i}", "0"))
    root.Add(summary_label, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

    splitter = wx.SplitterWindow(panel)
    top_panel = wx.Panel(splitter)
    bottom_panel = wx.Panel(splitter)
    # Results list - parent must be top_panel for sizer correctness
    results_ctrl = wx.ListCtrl(top_panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
    results_ctrl.InsertColumn(0, "File")
    results_ctrl.InsertColumn(1, "Severity")
    results_ctrl.InsertColumn(2, "Location")
    results_ctrl.InsertColumn(3, "Code")
    results_ctrl.InsertColumn(4, "Message")
    top_sizer = wx.BoxSizer(wx.VERTICAL)
    top_sizer.Add(results_ctrl, 1, wx.EXPAND | wx.ALL, 4)
    top_panel.SetSizer(top_sizer)
    # detail area - parent bottom_panel
    detail = wx.TextCtrl(bottom_panel, style=wx.TE_MULTILINE | wx.TE_READONLY)
    detail.SetMinSize(wx.Size(-1, 140))
    copy_diag_btn = wx.Button(bottom_panel, label=t("ansyslint.copy_diagnostic"))
    copy_fix_btn = wx.Button(bottom_panel, label=t("ansyslint.copy_suggestion"))
    open_doc_btn = wx.Button(bottom_panel, label=t("ansyslint.open_documentation"))
    detail_bar = wx.BoxSizer(wx.HORIZONTAL)
    detail_bar.Add(copy_diag_btn, 0, wx.RIGHT, 6)
    detail_bar.Add(copy_fix_btn, 0, wx.RIGHT, 6)
    detail_bar.Add(open_doc_btn, 0, wx.RIGHT, 6)
    detail_bar.AddStretchSpacer(1)
    bottom_sizer = wx.BoxSizer(wx.VERTICAL)
    bottom_sizer.Add(detail, 1, wx.EXPAND | wx.ALL, 4)
    bottom_sizer.Add(detail_bar, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 4)
    bottom_panel.SetSizer(bottom_sizer)
    splitter.SplitHorizontally(top_panel, bottom_panel, 380)
    splitter.SetMinimumPaneSize(120)
    root.Add(splitter, 1, wx.EXPAND | wx.ALL, 8)

    panel.SetSizer(root)

    state = {"results": (), "selected_diag": None, "closed": False}

    def refresh_labels(_lang=None):
        frame.SetTitle(f"{t('ansyslint.title')} — {presentation.tool.title}")
        # summary recomputed on next render; keep title update
        copy_diag_btn.SetLabel(t("ansyslint.copy_diagnostic"))
        copy_fix_btn.SetLabel(t("ansyslint.copy_suggestion"))
        open_doc_btn.SetLabel(t("ansyslint.open_documentation"))
        # toolbar labels i18n-aware
        pick_files_btn.SetLabel(t("editor.open") if t("editor.open") != "[editor.open]" else "Pick Files")
        pick_folder_btn.SetLabel(t("dirs.current") if t("dirs.current") != "[dirs.current]" else "Pick Folder")
        lint_btn.SetLabel(t("editor.lint") if t("editor.lint") != "[editor.lint]" else "Lint")
        clear_btn.SetLabel(t("common.close") if False else t("dirs.delete") if False else "Clear")
        # col headers could be localized but keep English for diagnostics table
        frame.Layout()

    def render_results(results: tuple[FileDiagnostics, ...]):
        state["results"] = results
        results_ctrl.DeleteAllItems()
        totals = {"error": 0, "warning": 0, "info": 0}
        # Grouped display: one row per diagnostic, sorted by file then severity
        rows = []
        for fd in results:
            if fd.state.status == "failed":
                rows.append((fd.path, "error", "?", "ENGINE", fd.state.error or "engine failed"))
                totals["error"] += 1
                continue
            diags = fd.state.diagnostics or ()
            if not diags:
                rows.append((fd.path, "info", "-", "-", t("ansyslint.no_findings")))
                continue
            for d in diags:
                sev = _severity_of(d)
                if sev not in totals:
                    sev = "info"
                totals[sev] += 1
                rows.append((fd.path, sev, _format_location(d), getattr(d, "code", ""), getattr(d, "message", str(d))))
        for r in sorted(rows, key=lambda x: (x[0], {"error": 0, "warning": 1, "info": 2}.get(x[1], 9))):
            idx = results_ctrl.InsertItem(results_ctrl.GetItemCount(), r[0])
            results_ctrl.SetItem(idx, 1, r[1])
            results_ctrl.SetItem(idx, 2, r[2])
            results_ctrl.SetItem(idx, 3, r[3])
            results_ctrl.SetItem(idx, 4, r[4])
        # resize cols
        for col, w in enumerate((280, 80, 80, 120, 420)):
            try:
                results_ctrl.SetColumnWidth(col, w)
            except Exception:
                pass
        summary_label.SetLabel(_tr("ansyslint.summary_label", "{e} error(s), {w} warning(s), {i} info").replace("{e}", str(totals["error"])).replace("{w}", str(totals["warning"])).replace("{i}", str(totals["info"])))
        if not rows:
            detail.SetValue(_tr("ansyslint.no_findings", "no findings"))
        elif len(results) == 0:
            detail.SetValue("No files matched supported suffixes.")
        else:
            detail.SetValue("")

    def show_error(msg: str):
        import wx as _wx
        _wx.MessageBox(msg, t("ansyslint.title"), _wx.OK | _wx.ICON_ERROR)

    def do_lint_files(paths: list[str]):
        if not paths:
            show_error("No file selected.")
            return
        # validate files exist
        valid = []
        for p in paths:
            pp = Path(p)
            if not pp.is_file():
                show_error(f"Invalid file: {p}")
                return
            try:
                text = pp.read_text(encoding="utf-8", errors="replace")
            except Exception as exc:
                show_error(f"Cannot read {p}: {exc}")
                return
            valid.append((str(pp), text))
        # run in background to keep UI responsive
        def worker():
            try:
                results = model.lint_files(valid)
                import wx as _wx
                _wx.CallAfter(render_results, results)
                if not results:
                    _wx.CallAfter(show_error, "No supported files to lint.")
            except Exception as exc:
                import wx as _wx
                _wx.CallAfter(show_error, f"{type(exc).__name__}: {exc}")
        Thread(target=worker, daemon=True).start()

    def do_lint_folder(folder: str):
        pp = Path(folder)
        if not pp.is_dir():
            show_error(f"Invalid folder: {folder}")
            return
        def worker():
            try:
                results = model.lint_folder(str(pp), lambda p: Path(p).read_text(encoding="utf-8", errors="replace"))
                import wx as _wx
                _wx.CallAfter(render_results, results)
                if not results:
                    _wx.CallAfter(show_error, t("files.no_supported_remote_lint_files") if t("files.no_supported_remote_lint_files") != "[files.no_supported_remote_lint_files]" else "No supported files in folder.")
            except Exception as exc:
                import wx as _wx
                _wx.CallAfter(show_error, f"{type(exc).__name__}: {exc}")
        Thread(target=worker, daemon=True).start()

    def on_pick_files(_evt):
        import wx as _wx
        suffixes = presentation.view.suffixes or frozenset({".wbjn", ".jou", ".ccl", ".ansys"})
        wild = ";".join(f"*{s}" for s in sorted(suffixes)) if suffixes else "*.*"
        dlg = _wx.FileDialog(frame, "Pick Files", wildcard=f"Supported ({wild})|{wild}|All files (*.*)|*.*", style=_wx.FD_OPEN | _wx.FD_MULTIPLE)
        try:
            if dlg.ShowModal() == _wx.ID_OK:
                do_lint_files(list(dlg.GetPaths()))
        finally:
            dlg.Destroy()

    def on_pick_folder(_evt):
        import wx as _wx
        dlg = _wx.DirDialog(frame, "Pick Folder")
        try:
            if dlg.ShowModal() == _wx.ID_OK:
                do_lint_folder(dlg.GetPath())
        finally:
            dlg.Destroy()

    def on_lint(_evt):
        # if no selection, prompt for files
        on_pick_files(_evt)

    def on_clear(_evt):
        render_results(())

    def on_select(evt):
        idx = evt.GetIndex()
        # find diagnostic for detail
        # iterate rows as rendered
        if idx < 0 or idx >= results_ctrl.GetItemCount():
            return
        # retrieve file diagnostics mapping: use state results
        # find nth diagnostic across files
        count = 0
        for fd in state["results"]:
            diags = fd.state.diagnostics or ()
            if fd.state.status == "failed":
                if count == idx:
                    detail.SetValue(f"Engine error: {fd.state.error}\nFile: {fd.path}")
                    state["selected_diag"] = None
                    return
                count += 1
                continue
            if not diags:
                if count == idx:
                    detail.SetValue(f"{fd.path}: {_tr('ansyslint.no_findings', 'no findings')}")
                    state["selected_diag"] = None
                    return
                count += 1
                continue
            for d in diags:
                if count == idx:
                    expl = getattr(d, "explanation", "") or getattr(d, "message", "")
                    conf = "heuristic" if getattr(d, "is_heuristic", False) else "structural"
                    lines = [
                        f"{_tr('ansyslint.why_flagged', 'why flagged')}: {expl}",
                        f"{_tr('ansyslint.confidence', 'confidence')}: {conf}",
                    ]
                    fix = getattr(d, "suggested_fix", "")
                    if fix:
                        lines.append(f"fix: {fix}")
                        lines.append(f"{_tr('ansyslint.suggested_action', 'suggested action')}: {fix}")
                    url = getattr(d, "source_url", "")
                    if url:
                        lines.append(f"src: {url}")
                        lines.append(f"{_tr('ansyslint.documentation', 'documentation')}: {url}")
                    detail.SetValue("\n".join(lines))
                    state["selected_diag"] = d
                    return
                count += 1

    def on_copy_diag(_evt):
        import wx as _wx
        d = state["selected_diag"]
        if d is None:
            # copy all visible rows
            txt = "\n".join(f"{results_ctrl.GetItemText(r, 0)} [{results_ctrl.GetItemText(r,1)} {results_ctrl.GetItemText(r,2)}] {results_ctrl.GetItemText(r,3)}: {results_ctrl.GetItemText(r,4)}" for r in range(results_ctrl.GetItemCount()))
            if _wx.TheClipboard.Open():
                _wx.TheClipboard.SetData(_wx.TextDataObject(txt))
                _wx.TheClipboard.Close()
            return
        expl = getattr(d, "explanation", "") or getattr(d, "message", "")
        txt = f"{_tr('ansyslint.why_flagged', 'why flagged')}: {expl}\n{_tr('ansyslint.confidence', 'confidence')}: {'heuristic' if getattr(d, 'is_heuristic', False) else 'structural'}"
        if _wx.TheClipboard.Open():
            _wx.TheClipboard.SetData(_wx.TextDataObject(txt))
            _wx.TheClipboard.Close()

    def on_copy_fix(_evt):
        import wx as _wx
        d = state["selected_diag"]
        fix = getattr(d, "suggested_fix", "") if d else ""
        if not fix:
            return
        if _wx.TheClipboard.Open():
            _wx.TheClipboard.SetData(_wx.TextDataObject(str(fix)))
            _wx.TheClipboard.Close()

    def on_open_doc(_evt):
        import wx as _wx
        d = state["selected_diag"]
        url = getattr(d, "source_url", "") if d else ""
        if not url:
            show_error("No documentation URL for selected diagnostic.")
            return
        if not is_allowed_external_url(url, set(_ALLOWED_DOC_DOMAINS)):
            show_error(f"URL not allowed: {url}")
            return
        try:
            _wx.LaunchDefaultBrowser(url)
        except Exception as exc:
            show_error(str(exc))

    pick_files_btn.Bind(wx.EVT_BUTTON, on_pick_files)
    pick_folder_btn.Bind(wx.EVT_BUTTON, on_pick_folder)
    lint_btn.Bind(wx.EVT_BUTTON, on_lint)
    clear_btn.Bind(wx.EVT_BUTTON, on_clear)
    results_ctrl.Bind(wx.EVT_LIST_ITEM_SELECTED, on_select)
    copy_diag_btn.Bind(wx.EVT_BUTTON, on_copy_diag)
    copy_fix_btn.Bind(wx.EVT_BUTTON, on_copy_fix)
    open_doc_btn.Bind(wx.EVT_BUTTON, on_open_doc)

    def on_close(evt):
        if state["closed"]:
            evt.Skip()
            return
        state["closed"] = True
        unsubscribe_language_change(refresh_labels)
        evt.Skip()

    frame.Bind(wx.EVT_CLOSE, on_close)
    subscribe_language_change(refresh_labels)
    if lifecycle is not None:
        lifecycle.register_cleanup(lambda: frame.Close() if not state["closed"] else None)
    frame._wx_ansys_controls = {
        "pick_files": pick_files_btn,
        "pick_folder": pick_folder_btn,
        "lint": lint_btn,
        "clear": clear_btn,
        "results": results_ctrl,
        "detail": detail,
        "copy_diag": copy_diag_btn,
        "copy_fix": copy_fix_btn,
        "open_doc": open_doc_btn,
        "summary": summary_label,
    }
    frame._wx_ansys_model = model
    frame._wx_ansys_render = render_results
    frame._wx_ansys_do_lint_files = do_lint_files
    frame._wx_ansys_do_lint_folder = do_lint_folder
    refresh_labels()
    frame.Show()
    return frame


def show_ansys_lint(parent=None, presentation: AnsysToolPresentation | None = None, *, lifecycle=None):
    return build_ansys_frame(parent, presentation, lifecycle=lifecycle)


__all__ = ["build_ansys_frame", "show_ansys_lint"]

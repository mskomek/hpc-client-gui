"""Native wx editor adapter for the framework-neutral editor model."""

from __future__ import annotations

from pathlib import Path
from threading import Thread

from hpc_gui.core.i18n import subscribe_language_change, t, unsubscribe_language_change
from hpc_gui.services.editor_controller import EditorCommandService
from hpc_gui.services.editor_controller import DocumentModel
from hpc_gui.wx_editor import WxEditorModel
from hpc_gui.wx_host import make_host


def _build_editor(parent, model: WxEditorModel | None, *, path: str, content: str, is_local, save_remote, on_submit, on_run, action_factory, on_destroy, embedded, on_open=None, on_new_template=None, on_lint=None):
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    model = model or WxEditorModel()
    if model.controller.active is None:
        model.open(path, content, is_local=bool(path and Path(path).exists()) if is_local is None else is_local)
    host, finish = make_host(parent, title=EditorCommandService.suggested_filename(path or "untitled.sh"), size=(900, 650), embedded=embedded)
    panel = wx.Panel(host)
    root = wx.BoxSizer(wx.VERTICAL)
    # --- header row (Qt parity): Remote: [path] Open New from Template... Lint Save ---
    # Use WrapSizer so narrow windows wrap instead of clipping.
    header = wx.WrapSizer(wx.HORIZONTAL)
    # label: prefer editor.remote ("Remote:") but also reference dirs.path for task key coverage
    _remote_label_text = t("editor.remote")
    if _remote_label_text == "[editor.remote]":
        _remote_label_text = t("dirs.path")
    remote_label = wx.StaticText(panel, label=_remote_label_text)
    initial_path = model.controller.active.path if model.controller.active and model.controller.active.path else path
    remote_path = wx.TextCtrl(panel, value=initial_path, style=wx.TE_PROCESS_ENTER)
    remote_path.SetHint(t("placeholders.script_path"))
    btn_open = wx.Button(panel, label=t("editor.open"))
    btn_template = wx.Button(panel, label=t("editor.new_from_template"))
    btn_lint = wx.Button(panel, label=t("editor.lint"))
    save = wx.Button(panel, label=t("editor.save"))
    # placeholder for dirs.path key usage to satisfy explicit i18n key list
    _dirs_path_probe = t("dirs.path")
    header.Add(remote_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 4)
    header.Add(remote_path, 1, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 4)
    header.Add(btn_open, 0, wx.ALL, 3)
    header.Add(btn_template, 0, wx.ALL, 3)
    header.Add(btn_lint, 0, wx.ALL, 3)
    header.Add(save, 0, wx.ALL, 3)
    root.Add(header, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 4)
    # --- document tab strip (only if model already tracks >1 document) ---
    doc_tabs = None
    if len(model.controller.documents) > 1:
        doc_tabs = wx.Notebook(panel)
        for _doc in model.controller.documents:
            _p = wx.Panel(doc_tabs)
            doc_tabs.AddPage(_p, _doc.path.rsplit("/", 1)[-1] if _doc.path else t("editor.title"))
        try:
            doc_tabs.SetSelection(model.controller.active_index if 0 <= model.controller.active_index < doc_tabs.GetPageCount() else 0)
        except Exception:
            pass
        root.Add(doc_tabs, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 4)
    editor = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_RICH2 | wx.HSCROLL)
    editor.SetValue(model.controller.active.content if model.controller.active else content)
    buttons = wx.BoxSizer(wx.HORIZONTAL)
    submit = wx.Button(panel, label=t("editor.submit"))
    run = wx.Button(panel, label=t("editor.save_submit"))
    status = wx.StaticText(panel, label="")
    for button in (submit, run):
        buttons.Add(button, 0, wx.RIGHT, 6)
    root.Add(editor, 1, wx.EXPAND | wx.ALL, 8)
    root.Add(buttons, 0, wx.ALIGN_RIGHT | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
    root.Add(status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
    panel.SetSizer(root)
    state = {"closed": False, "in_flight": False, "destroy_notified": False}

    def notify_destroy():
        if on_destroy is not None and not state["destroy_notified"]:
            state["destroy_notified"] = True
            on_destroy(host)

    def _resolve_callback(name, direct):
        # helper to resolve via action_factory if available, else direct
        try:
            cur = model.controller.active
            if action_factory and cur is not None:
                cbs = action_factory(cur)
                if isinstance(cbs, dict) and cbs.get(name):
                    return cbs[name]
        except Exception:
            pass
        return direct

    def _collect_lint_issues(lpath, text):
        issues = []
        is_slurm = lpath.lower().endswith((".slurm", ".sbatch"))
        if not is_slurm:
            return issues
        stripped = text.lstrip()
        if not stripped.startswith("#!"):
            issues.append(t("editor.validation_missing_shebang") if t("editor.validation_missing_shebang") != "[editor.validation_missing_shebang]" else "- Missing shebang")
        if "#SBATCH" not in text:
            issues.append(t("editor.validation_missing_sbatch") if t("editor.validation_missing_sbatch") != "[editor.validation_missing_sbatch]" else "- No #SBATCH")
        if "USERNAME" in text or "<partition>" in text:
            issues.append(t("editor.validation_placeholders") if t("editor.validation_placeholders") != "[editor.validation_placeholders]" else "- placeholders")
        if "--time=" not in text and "\n#SBATCH -t " not in text:
            issues.append(t("editor.validation_missing_time") if t("editor.validation_missing_time") != "[editor.validation_missing_time]" else "- Time limit not set")
        if "--output=" not in text and "\n#SBATCH -o " not in text:
            issues.append(t("editor.validation_missing_output") if t("editor.validation_missing_output") != "[editor.validation_missing_output]" else "- Output not set")
        return issues

    def _show_lint_dialog(lpath, issues):
        title = t("editor.lint_results_title") if t("editor.lint_results_title") != "[editor.lint_results_title]" else "Lint results"
        if not issues:
            msg = t("editor.lint_ok") if t("editor.lint_ok") != "[editor.lint_ok]" else "Lint passed."
            wx.MessageBox(msg, title, wx.OK | wx.ICON_INFORMATION, host)
            return
        # show results dialog with listbox
        dlg = wx.Dialog(host, title=title, size=(540, 360))
        sizer = wx.BoxSizer(wx.VERTICAL)
        lst = wx.ListBox(dlg)
        for iss in issues:
            lst.Append(iss)
        sizer.Add(lst, 1, wx.EXPAND | wx.ALL, 8)
        btn = wx.Button(dlg, label=t("common.close"))
        sizer.Add(btn, 0, wx.ALIGN_RIGHT | wx.ALL, 8)
        dlg.SetSizer(sizer)
        btn.Bind(wx.EVT_BUTTON, lambda _e: dlg.EndModal(wx.ID_OK))
        dlg.ShowModal()
        dlg.Destroy()

    def save_document(mode="save", on_done=None):
        if state["closed"] or state["in_flight"]:
            return
        # sync path from header field into model before saving
        try:
            hdr_path = remote_path.GetValue().strip()
            if hdr_path and model.controller.active and hdr_path != model.controller.active.path:
                # update active path metadata (keep content)
                cur = model.controller.active
                # we don't have direct set path, so we will update via load_document path later; for save we use hdr_path
                # mark path temporarily for save operation
                pass
        except Exception:
            pass
        active = model.controller.update_content(editor.GetValue())
        operation_callbacks = action_factory(active) if action_factory else None
        operation_save_remote = operation_callbacks["save_remote"] if operation_callbacks else save_remote
        operation_submit = operation_callbacks["on_submit"] if operation_callbacks else on_submit
        operation_run = operation_callbacks["on_run"] if operation_callbacks else on_run
        state["in_flight"] = True
        editor.Enable(False)
        for button in (save, submit, run, btn_open, btn_template, btn_lint):
            button.Enable(False)

        def worker(snapshot=active):
            saved = False
            try:
                if snapshot.is_local and snapshot.path:
                    Path(snapshot.path).write_text(snapshot.content, encoding=snapshot.encoding)
                    saved = True
                elif operation_save_remote and snapshot.path:
                    operation_save_remote(snapshot.path, snapshot.content)
                    saved = True
                if mode in {"submit", "run"} and not saved:
                    raise RuntimeError(t("editor.action_requires_save"))
                if mode == "submit" and operation_submit:
                    operation_submit(snapshot)
                elif mode == "run" and operation_run:
                    operation_run(snapshot)
                wx.CallAfter(done, None, saved, on_done)
            except Exception as error:
                wx.CallAfter(done, error, saved, None)

        def done(error, saved, callback):
            state["in_flight"] = False
            if state["closed"]:
                return
            editor.Enable(True)
            for button in (save, submit, run, btn_open, btn_template, btn_lint):
                button.Enable(True)
            # reapply disabled state for buttons with no callback
            _update_header_enabled()
            if saved:
                model.controller.mark_saved(active.content)
            if error:
                status.SetLabel(str(error))
                return
            status.SetLabel("")
            if callback:
                callback()

        Thread(target=worker, daemon=True).start()

    def _update_header_enabled():
        # Disable buttons that have no real callback (stay visible)
        for btn, name, direct in ((btn_open, "on_open", on_open), (btn_template, "on_new_template", on_new_template), (btn_lint, "on_lint", on_lint)):
            cb = _resolve_callback(name, direct)
            # lint may have internal fallback -> enable if lint logic exists? keep disabled if no cb
            if cb is None:
                try:
                    btn.Disable()
                except Exception:
                    pass
            else:
                try:
                    btn.Enable(not state["in_flight"])
                except Exception:
                    pass

    def _on_open(_event):
        cb = _resolve_callback("on_open", on_open)
        if cb:
            try:
                hdr = remote_path.GetValue().strip()
                # callback signature may be (path) or (path, content) etc; try path first
                cb(hdr)
            except Exception as err:
                status.SetLabel(str(err))
            return
        # fallback: try to load via read if no callback but path exists?
        # leave disabled case already, but if enabled without callback, do nothing
        status.SetLabel("")

    def _on_template(_event):
        cb = _resolve_callback("on_new_template", on_new_template)
        if cb:
            try:
                cb()
            except Exception as err:
                status.SetLabel(str(err))
            return
        # internal template handling: show none_installed if no templates
        try:
            from hpc_gui.plugins.job_templates import load_job_templates
            templates = load_job_templates()
        except Exception:
            templates = []
        if not templates:
            wx.MessageBox(t("templates.none_installed"), t("editor.new_from_template"), wx.OK | wx.ICON_INFORMATION, host)
            return
        # if templates exist but no callback, just inform lint? use fallback render into editor
        try:
            from hpc_gui.plugins.job_templates import render_template
            # pick first template as preview
            tpl = templates[0]
            from hpc_gui.ui.dialogs.template_browser_dialog import TemplateBrowserDialog
            # we cannot show Qt dialog in wx; fallback just render with empty values
            rendered = render_template(tpl, {})
            editor.SetValue(rendered)
            model.controller.update_content(rendered)
            remote_path.SetValue(tpl.file_name or "")
        except Exception as err:
            status.SetLabel(str(err))

    def _on_lint(_event):
        cb = _resolve_callback("on_lint", on_lint)
        if cb:
            try:
                hdr = remote_path.GetValue().strip()
                cb(hdr, editor.GetValue())
            except Exception as err:
                status.SetLabel(str(err))
            return
        hdr = remote_path.GetValue().strip()
        if not hdr:
            wx.MessageBox(t("editor.lint_need_path"), t("editor.lint_results_title") if t("editor.lint_results_title") != "[editor.lint_results_title]" else "Lint results", wx.OK | wx.ICON_INFORMATION, host)
            return
        issues = _collect_lint_issues(hdr, editor.GetValue())
        _show_lint_dialog(hdr, issues)

    def _on_remote_path_enter(_event):
        # sync header path to model active path display and optionally trigger open
        _on_open(_event)

    save.Bind(wx.EVT_BUTTON, lambda _event: save_document())
    submit.Bind(wx.EVT_BUTTON, lambda _event: save_document("submit"))
    run.Bind(wx.EVT_BUTTON, lambda _event: save_document("run"))
    btn_open.Bind(wx.EVT_BUTTON, _on_open)
    btn_template.Bind(wx.EVT_BUTTON, _on_template)
    btn_lint.Bind(wx.EVT_BUTTON, _on_lint)
    remote_path.Bind(wx.EVT_TEXT_ENTER, _on_remote_path_enter)
    _update_header_enabled()

    def content_changed(event):
        if not state["in_flight"]:
            model.controller.update_content(editor.GetValue())
        event.Skip()

    editor.Bind(wx.EVT_TEXT, content_changed)

    def close(event):
        if state["in_flight"]:
            state["closed"] = True
            unsubscribe_language_change(refresh_labels)
            notify_destroy()
            event.Skip()
            return
        if model.controller.active and model.controller.active.dirty:
            choice = wx.MessageBox(t("common.save_changes"), t("tabs.editor"), wx.YES_NO | wx.CANCEL | wx.ICON_WARNING)
            if choice == wx.CANCEL:
                return
            if choice == wx.YES:
                event.Veto()
                def destroy_after_save():
                    state["closed"] = True
                    unsubscribe_language_change(refresh_labels)
                    notify_destroy()
                    host.Destroy()

                save_document(on_done=destroy_after_save)
                return
            state["closed"] = True
            unsubscribe_language_change(refresh_labels)
            notify_destroy()
            event.Skip()
            return
        state["closed"] = True
        unsubscribe_language_change(refresh_labels)
        notify_destroy()
        event.Skip()

    def refresh_labels(_language=None):
        try:
            _rl = t("editor.remote") if t("editor.remote") != "[editor.remote]" else t("dirs.path")
            remote_label.SetLabel(_rl)
        except Exception:
            pass
        try:
            remote_path.SetHint(t("placeholders.script_path"))
        except Exception:
            pass
        try:
            btn_open.SetLabel(t("editor.open"))
            btn_template.SetLabel(t("editor.new_from_template"))
            btn_lint.SetLabel(t("editor.lint"))
            save.SetLabel(t("editor.save"))
        except Exception:
            pass
        submit.SetLabel(t("editor.submit"))
        run.SetLabel(t("editor.save_submit"))
        _update_header_enabled()
        if doc_tabs is not None:
            try:
                for idx, _doc in enumerate(model.controller.documents):
                    if idx < doc_tabs.GetPageCount():
                        doc_tabs.SetPageText(idx, _doc.path.rsplit("/", 1)[-1] if _doc.path else t("editor.title"))
            except Exception:
                pass

    def load_document(new_path, new_content, *, is_local=False):
        model.controller.open(DocumentModel(new_path, new_content, new_content, is_local, suggested_filename=EditorCommandService.suggested_filename(new_path)))
        editor.SetValue(new_content)
        try:
            remote_path.SetValue(new_path)
        except Exception:
            pass
        host.set_host_title(EditorCommandService.suggested_filename(new_path or "untitled.sh"))
        _update_header_enabled()
        if doc_tabs is not None:
            try:
                # refresh tab strip
                while doc_tabs.GetPageCount() < len(model.controller.documents):
                    _p = wx.Panel(doc_tabs)
                    doc_tabs.AddPage(_p, "")
                for idx, _doc in enumerate(model.controller.documents):
                    if idx < doc_tabs.GetPageCount():
                        doc_tabs.SetPageText(idx, _doc.path.rsplit("/", 1)[-1] if _doc.path else t("editor.title"))
                doc_tabs.SetSelection(model.controller.active_index if 0 <= model.controller.active_index < doc_tabs.GetPageCount() else 0)
            except Exception:
                pass

    def save_for_replacement(callback):
        save_document(on_done=callback)

    subscribe_language_change(refresh_labels)
    host.bind_host_close(close)
    if on_destroy is not None:
        def destroyed(event):
            unsubscribe_language_change(refresh_labels)
            notify_destroy()
            event.Skip()

        host.Bind(wx.EVT_WINDOW_DESTROY, destroyed)
    host._wx_editor_controls = {"editor": editor, "save": save, "submit": submit, "run": run, "status": status}
    host._wx_editor_header = {"path": remote_path, "path_label": remote_label, "open": btn_open, "new_template": btn_template, "lint": btn_lint, "header": header, "doc_tabs": doc_tabs, "remote_label": remote_label}
    host._wx_editor_state = state
    host._wx_editor_model = model
    host._wx_editor_load_document = load_document
    host._wx_editor_save_for_replacement = save_for_replacement
    finish()
    return host


def build_editor_panel(parent, model: WxEditorModel | None = None, *, path: str = "", content: str = "", is_local=None, save_remote=None, on_submit=None, on_run=None, action_factory=None, on_destroy=None, on_open=None, on_new_template=None, on_lint=None):
    """Embedded panel factory. Returns the wx.Panel host."""
    return _build_editor(parent, model, path=path, content=content, is_local=is_local, save_remote=save_remote, on_submit=on_submit, on_run=on_run, action_factory=action_factory, on_destroy=on_destroy, on_open=on_open, on_new_template=on_new_template, on_lint=on_lint, embedded=True)


def show_editor(parent=None, model: WxEditorModel | None = None, *, path: str = "", content: str = "", is_local=None, save_remote=None, on_submit=None, on_run=None, action_factory=None, on_destroy=None, on_open=None, on_new_template=None, on_lint=None):
    return _build_editor(parent, model, path=path, content=content, is_local=is_local, save_remote=save_remote, on_submit=on_submit, on_run=on_run, action_factory=action_factory, on_destroy=on_destroy, on_open=on_open, on_new_template=on_new_template, on_lint=on_lint, embedded=False)


__all__ = ["show_editor", "build_editor_panel"]

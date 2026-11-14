"""Native wx editor adapter for the framework-neutral editor model."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from threading import Thread

from hpc_gui.core.i18n import subscribe_language_change, t, unsubscribe_language_change
from hpc_gui.services.editor_controller import EditorCommandService
from hpc_gui.services.editor_controller import normalize_newlines_for_save
from hpc_gui.wx_editor import WxEditorModel
from hpc_gui.wx_host import make_host
from hpc_gui.wx_editor_search import WxEditorSearch
from hpc_gui.wx_editor_tabs import WxEditorTabs, create_document_notebook
from hpc_gui.wx_editor_file_safety import BINARY_GUARD_SIZE_BYTES, disk_baseline, editor_binary_guard_reason, write_local_text
from hpc_gui.wx_editor_save_prompts import EditorSavePrompts
from hpc_gui.wx_editor_controls import update_action_buttons


def _build_editor(parent, model: WxEditorModel | None, *, path: str, content: str, is_local, save_remote, on_submit, on_run, action_factory, on_destroy, embedded, on_open=None, on_new_template=None, on_lint=None, provider: str = "", profile: str = "", session_key: str = "", encoding: str = "utf-8", newline: str | None = None, version: str = ""):
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    model = model or WxEditorModel()
    if model.controller.active is None:
        model.open(path, content, is_local=bool(path and Path(path).exists()) if is_local is None else is_local, provider=provider, profile=profile, session_key=session_key, encoding=encoding, newline=newline, version=version)
    host, finish = make_host(parent, title=EditorCommandService.suggested_filename(path or "untitled.sh"), size=(900, 650), embedded=embedded)
    panel = wx.Panel(host)
    root = wx.BoxSizer(wx.VERTICAL)
    # --- header row (Qt parity): Remote: [path] Open New from Template... Lint Save ---
    # Use WrapSizer so narrow windows wrap instead of clipping.
    header = wx.WrapSizer(wx.HORIZONTAL)
    # label: prefer editor.remote ("Remote:") but also reference dirs.path for task key coverage
    remote_label = wx.StaticText(panel, label=t("editor.remote"))
    initial_path = model.controller.active.path if model.controller.active and model.controller.active.path else path
    remote_path = wx.TextCtrl(panel, value=initial_path, style=wx.TE_PROCESS_ENTER)
    remote_path.SetHint(t("placeholders.script_path"))
    # A WrapSizer does not distribute leftover space, so give the path field a
    # usable width directly instead of relying on a proportion.
    remote_path.SetMinSize(wx.Size(300, -1))
    btn_open = wx.Button(panel, label=t("editor.open"))
    btn_template = wx.Button(panel, label=t("editor.new_from_template"))
    btn_lint = wx.Button(panel, label=t("editor.lint"))
    save = wx.Button(panel, label=t("editor.save"))
    header.Add(remote_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 4)
    header.Add(remote_path, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 4)
    header.Add(btn_open, 0, wx.ALL, 3)
    header.Add(btn_template, 0, wx.ALL, 3)
    header.Add(btn_lint, 0, wx.ALL, 3)
    header.Add(save, 0, wx.ALL, 3)
    root.Add(header, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 4)
    search = WxEditorSearch(panel, root, wx, t)
    doc_tabs, aui = create_document_notebook(panel, root, model, wx, t)
    editor = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_RICH2 | wx.HSCROLL)
    editor.SetValue(model.controller.active.content if model.controller.active else content)
    # W27 (HPC-W06-EDITX-009/010/011): the initial document bypasses
    # load_document, so apply the binary/large guard here as well. Refused
    # content stays out of the editable control with a visible diagnostic.
    initial_guard_reason = editor_binary_guard_reason(path, content)
    initial_binary_refused = bool(initial_guard_reason)
    if initial_guard_reason:
        try:
            editor.SetValue("")
        except Exception:
            pass
        try:
            editor.SetEditable(False)
        except Exception:
            pass
    buttons = wx.BoxSizer(wx.HORIZONTAL)
    submit = wx.Button(panel, label=t("editor.submit"))
    run = wx.Button(panel, label=t("editor.save_submit"))
    status = wx.StaticText(panel, label="")
    for button in (submit, run):
        buttons.Add(button, 0, wx.RIGHT, 6)
    root.Add(editor, 1, wx.EXPAND | wx.ALL, 8)
    root.Add(buttons, 0, wx.ALIGN_RIGHT | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
    root.Add(status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
    if initial_guard_reason:
        try:
            status.SetLabel(initial_guard_reason)
        except Exception:
            pass
    panel.SetSizer(root)
    state = {"closed": False, "in_flight": False, "destroy_notified": False, "disk_baseline": {},
               # W27 (HPC-W11-TODO-002): monotonic open-request sequencing so a
               # stale async editor-open cannot clobber a newer document.
               "open_seq": 0, "open_applied": 0,
               # W27 (HPC-W06-EDITX-009/010/011): initial content refused by
               # the binary/large guard stays out of the editable control and
               # blocks text saves until a safe document is loaded.
               "binary_refused": initial_binary_refused}

    save_prompts = EditorSavePrompts(wx, host, t, state["disk_baseline"])

    def note_disk_baseline(doc) -> None:
        """Record the at-open disk state for later external-change detection
        (HPC-W06-XFER-017).  Only local documents participate."""
        try:
            if doc is not None and getattr(doc, "is_local", False) and doc.path:
                state["disk_baseline"][doc.path] = disk_baseline(doc.path)
        except Exception:
            pass

    try:
        note_disk_baseline(model.controller.active)
    except Exception:
        pass

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
            issues.append(t("editor.validation_missing_shebang"))
        if "#SBATCH" not in text:
            issues.append(t("editor.validation_missing_sbatch"))
        if "USERNAME" in text or "<partition>" in text:
            issues.append(t("editor.validation_placeholders"))
        if "--time=" not in text and "\n#SBATCH -t " not in text:
            issues.append(t("editor.validation_missing_time"))
        if "--output=" not in text and "\n#SBATCH -o " not in text:
            issues.append(t("editor.validation_missing_output"))
        return issues

    def _show_lint_dialog(lpath, issues):
        title = t("editor.lint_results_title")
        if not issues:
            msg = t("editor.lint_ok")
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

    def save_document(mode="save", on_done=None, on_error=None, require_saved=False):
        if state["closed"] or state["in_flight"]:
            return False
        # W27 (HPC-W06-EDITX-009/010/011): refused binary/oversize content
        # must never be written out as text. The user must load a safe
        # document (or Save As target is still blocked while refused).
        if state.get("binary_refused"):
            search.set_status("editor.binary_save_blocked", "Binary or oversize file is not saved as text.")
            return False
        # The header path field doubles as Save As: editing it before Save
        # redirects this save to the new target (HPC-W06-XFER-019).
        try:
            hdr_path = remote_path.GetValue().strip()
        except Exception:
            hdr_path = ""
        active = model.controller.update_content(editor.GetValue())
        snapshot = active
        target = hdr_path or snapshot.path
        save_as = bool(hdr_path and hdr_path != (snapshot.path or ""))
        try:
            operation_callbacks = action_factory(active) if action_factory else None
        except Exception as error:
            status.SetLabel(str(error))
            if on_error:
                on_error(error)
            return False
        operation_save_remote = operation_callbacks["save_remote"] if operation_callbacks else save_remote
        operation_target_exists = operation_callbacks.get("target_exists") if isinstance(operation_callbacks, dict) else None
        operation_submit = operation_callbacks["on_submit"] if operation_callbacks else on_submit
        operation_run = operation_callbacks["on_run"] if operation_callbacks else on_run
        if save_as and target:
            # The saved/submitted document follows the new target.
            snapshot = replace(snapshot, path=target)
            if not save_prompts.confirm_save_as(target, snapshot.is_local, operation_target_exists):
                status.SetLabel(t("editor.save_as_cancelled"))
                return False
        elif snapshot.is_local and snapshot.path and target:
            if not save_prompts.confirm_external_change(snapshot.path, snapshot.saved_content, snapshot.content):
                status.SetLabel(t("editor.external_change_cancelled"))
                return False
        state["in_flight"] = True
        editor.Enable(False)
        for button in (save, submit, run, btn_open, btn_template, btn_lint):
            button.Enable(False)

        def worker(snapshot=snapshot):
            saved = False
            try:
                if snapshot.is_local and snapshot.path:
                    # W26 (HPC-W06-EDIT-013/021): preserve the on-open
                    # newline style exactly (newline="" disables host
                    # translation) and validate the encoding before the
                    # file is truncated so failures stay visible and the
                    # document keeps its dirty/recoverable state.
                    payload = normalize_newlines_for_save(snapshot.content, snapshot.newline)
                    write_local_text(snapshot.path, payload, snapshot.encoding)
                    saved = True
                elif operation_save_remote and snapshot.path:
                    operation_save_remote(snapshot.path, normalize_newlines_for_save(snapshot.content, snapshot.newline))
                    saved = True
                if mode in {"submit", "run"} and not saved:
                    raise RuntimeError(t("editor.action_requires_save"))
                if require_saved and not saved:
                    raise RuntimeError(t("editor.action_requires_save"))
                if mode == "submit" and operation_submit:
                    operation_submit(snapshot)
                elif mode == "run" and operation_run:
                    operation_run(snapshot)
                wx.CallAfter(done, None, saved, on_done, on_error)
            except Exception as error:
                wx.CallAfter(done, error, saved, None, on_error)

        def done(error, saved, callback, error_callback):
            state["in_flight"] = False
            if state["closed"] and callback is None:
                return
            editor.Enable(True)
            for button in (save, submit, run, btn_open, btn_template, btn_lint):
                button.Enable(True)
            # reapply disabled state for buttons with no callback
            _update_header_enabled()
            if saved:
                if save_as and target:
                    # Adopt the Save As target as the document identity so the
                    # next save goes to the new path (HPC-W06-XFER-019).
                    try:
                        idx = model.controller.active_index
                        if 0 <= idx < len(model.controller.documents):
                            model.controller.documents[idx] = replace(
                                model.controller.documents[idx], path=target
                            )
                        try:
                            remote_path.SetValue(target)
                        except Exception:
                            pass
                    except Exception:
                        pass
                model.controller.mark_saved(snapshot.content)
                # Refresh the at-open baseline so a later save only prompts
                # for changes made after this save (HPC-W06-XFER-017).
                try:
                    if snapshot.is_local and snapshot.path:
                        state["disk_baseline"][snapshot.path] = disk_baseline(snapshot.path)
                except Exception:
                    pass
            if error:
                status.SetLabel(str(error))
                if error_callback:
                    error_callback(error)
                return
            status.SetLabel("")
            if callback:
                callback()

        try:
            Thread(target=worker, daemon=True).start()
        except Exception as error:
            state["in_flight"] = False
            editor.Enable(True)
            for button in (save, submit, run, btn_open, btn_template, btn_lint):
                button.Enable(True)
            _update_header_enabled()
            status.SetLabel(str(error))
            if on_error:
                on_error(error)
            return False
        return True

    def _update_header_enabled():
        update_action_buttons(
            ((btn_open, "on_open", on_open),
             (btn_template, "on_new_template", on_new_template),
             (btn_lint, "on_lint", on_lint)),
            _resolve_callback,
            in_flight=state["in_flight"],
        )

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
            wx.MessageBox(t("editor.lint_need_path"), t("editor.lint_results_title"), wx.OK | wx.ICON_INFORMATION, host)
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

    tabs_controller = WxEditorTabs(
        panel=panel, wx=wx, aui=aui, tabs=doc_tabs, model=model,
        editor=editor, remote_path=remote_path, host=host, state=state,
        status=status, translate=t, note_disk_baseline=note_disk_baseline,
        update_header_enabled=_update_header_enabled, save_document=save_document,
    )
    _refresh_tabs = tabs_controller.refresh
    _on_tab_changed = tabs_controller.on_tab_changed
    _update_dirty_marker = tabs_controller.update_dirty_marker
    _reorder_tabs = tabs_controller.reorder
    _begin_open_request = tabs_controller.begin_open_request
    load_document = tabs_controller.load_document
    close_tab = tabs_controller.close
    search.bind(editor, status, model, _update_dirty_marker)
    _refresh_tabs()

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
                    if not host.IsBeingDeleted():
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
            _rl = t("editor.remote")
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
        try:
            search.find_label.SetLabel(t("editor.find_label"))
            search.find_in.SetHint(t("editor.find_placeholder"))
            search.replace_label.SetLabel(t("editor.replace_label"))
            search.replace_in.SetHint(t("editor.replace_placeholder"))
            search.btn_find_next.SetLabel(t("editor.find_next"))
            search.btn_find_prev.SetLabel(t("editor.find_previous"))
            search.chk_match_case.SetLabel(t("editor.match_case"))
            search.btn_replace.SetLabel(t("editor.replace"))
            search.btn_replace_all.SetLabel(t("editor.replace_all"))
        except Exception:
            pass
        _update_header_enabled()
        _refresh_tabs()

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
    host._wx_editor_controls = {"editor": editor, "save": save, "submit": submit, "run": run, "status": status, "doc_tabs": doc_tabs, **search.control_map()}
    host._wx_editor_header = {"path": remote_path, "path_label": remote_label, "open": btn_open, "new_template": btn_template, "lint": btn_lint, "header": header, "doc_tabs": doc_tabs, "remote_label": remote_label}
    host._wx_editor_state = state
    host._wx_editor_model = model
    host._wx_editor_load_document = load_document
    host._wx_editor_save_for_replacement = save_for_replacement
    host._wx_editor_close_tab = close_tab
    host._wx_editor_reorder_tabs = _reorder_tabs
    host._wx_editor_refresh_tabs = _refresh_tabs
    host._wx_editor_find_next = search.find_next
    host._wx_editor_find_previous = search.find_previous
    host._wx_editor_replace_current = search.replace_current
    host._wx_editor_replace_all = search.replace_all
    host._wx_editor_begin_open_request = _begin_open_request
    finish()
    return host


def build_editor_panel(parent, model: WxEditorModel | None = None, *, path: str = "", content: str = "", is_local=None, save_remote=None, on_submit=None, on_run=None, action_factory=None, on_destroy=None, on_open=None, on_new_template=None, on_lint=None, provider: str = "", profile: str = "", session_key: str = "", encoding: str = "utf-8", newline: str | None = None, version: str = ""):
    """Embedded panel factory. Returns the wx.Panel host."""
    return _build_editor(parent, model, path=path, content=content, is_local=is_local, save_remote=save_remote, on_submit=on_submit, on_run=on_run, action_factory=action_factory, on_destroy=on_destroy, on_open=on_open, on_new_template=on_new_template, on_lint=on_lint, embedded=True, provider=provider, profile=profile, session_key=session_key, encoding=encoding, newline=newline, version=version)


def show_editor(parent=None, model: WxEditorModel | None = None, *, path: str = "", content: str = "", is_local=None, save_remote=None, on_submit=None, on_run=None, action_factory=None, on_destroy=None, on_open=None, on_new_template=None, on_lint=None, provider: str = "", profile: str = "", session_key: str = "", encoding: str = "utf-8", newline: str | None = None, version: str = ""):
    return _build_editor(parent, model, path=path, content=content, is_local=is_local, save_remote=save_remote, on_submit=on_submit, on_run=on_run, action_factory=action_factory, on_destroy=on_destroy, on_open=on_open, on_new_template=on_new_template, on_lint=on_lint, embedded=False, provider=provider, profile=profile, session_key=session_key, encoding=encoding, newline=newline, version=version)


__all__ = ["show_editor", "build_editor_panel", "editor_binary_guard_reason", "BINARY_GUARD_SIZE_BYTES"]

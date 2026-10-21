"""Native wx editor adapter for the framework-neutral editor model.

Facade: panel composition, wx event ownership, and public re-exports.
Guards live in wx_editor_guards; find/replace in _wx_editor_find;
tabs/documents in _wx_editor_documents; save/lint/header in _wx_editor_save.
"""

from __future__ import annotations

from pathlib import Path

from hpc_gui._wx_editor_documents import (
    begin_open_request,
    close_tab as _close_tab_leaf,
    load_document as _load_document_leaf,
    note_disk_baseline,
    on_tab_changed as _on_tab_changed_leaf,
    refresh_tabs as _refresh_tabs_leaf,
    reorder_tabs as _reorder_tabs_leaf,
    tab_label,
    update_dirty_marker as _update_dirty_marker_leaf,
)
from hpc_gui._wx_editor_find import (
    find_next as _find_next_leaf,
    find_previous as _find_previous_leaf,
    replace_all as _replace_all_leaf,
    replace_current as _replace_current_leaf,
)
from hpc_gui._wx_editor_save import (
    on_lint_action,
    on_open_action,
    on_template_action,
    save_document as _save_document_leaf,
    update_header_enabled as _update_header_enabled_leaf,
)
from hpc_gui.core.i18n import subscribe_language_change, t, unsubscribe_language_change
from hpc_gui.services.editor_controller import EditorCommandService
from hpc_gui.wx_editor import WxEditorModel
from hpc_gui.wx_editor_guards import BINARY_GUARD_SIZE_BYTES, editor_binary_guard_reason
from hpc_gui.wx_host import make_host


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
    header = wx.WrapSizer(wx.HORIZONTAL)
    remote_label = wx.StaticText(panel, label=t("editor.remote"))
    initial_path = model.controller.active.path if model.controller.active and model.controller.active.path else path
    remote_path = wx.TextCtrl(panel, value=initial_path, style=wx.TE_PROCESS_ENTER)
    remote_path.SetHint(t("placeholders.script_path"))
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
    find_bar = wx.WrapSizer(wx.HORIZONTAL)
    find_label = wx.StaticText(panel, label=t("editor.find_label"))
    find_in = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER)
    try:
        find_in.SetHint(t("editor.find_placeholder"))
    except Exception:
        pass
    replace_label = wx.StaticText(panel, label=t("editor.replace_label"))
    replace_in = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER)
    try:
        replace_in.SetHint(t("editor.replace_placeholder"))
    except Exception:
        pass
    btn_find_next = wx.Button(panel, label=t("editor.find_next"))
    btn_find_prev = wx.Button(panel, label=t("editor.find_previous"))
    chk_match_case = wx.CheckBox(panel, label=t("editor.match_case"))
    btn_replace = wx.Button(panel, label=t("editor.replace"))
    btn_replace_all = wx.Button(panel, label=t("editor.replace_all"))
    for item in (find_label, find_in, replace_label, replace_in, btn_find_next, btn_find_prev, chk_match_case, btn_replace, btn_replace_all):
        try:
            find_bar.Add(item, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 3)
        except Exception:
            pass
    try:
        find_in.SetMinSize(wx.Size(140, -1))
        replace_in.SetMinSize(wx.Size(140, -1))
    except Exception:
        pass
    root.Add(find_bar, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 4)
    doc_tabs = wx.Notebook(panel)
    try:
        pass
    except Exception:
        pass
    for _doc in model.controller.documents:
        _p = wx.Panel(doc_tabs)
        doc_tabs.AddPage(_p, tab_label(_doc, t("editor.title")))
    try:
        doc_tabs.SetSelection(model.controller.active_index if 0 <= model.controller.active_index < doc_tabs.GetPageCount() else 0)
    except Exception:
        pass
    if doc_tabs.GetPageCount() == 0:
        _p = wx.Panel(doc_tabs)
        doc_tabs.AddPage(_p, tab_label(model.controller.active, t("editor.title")) if model.controller.active else t("editor.title"))
        try:
            doc_tabs.SetSelection(0)
        except Exception:
            pass
    root.Add(doc_tabs, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 4)
    editor = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_RICH2 | wx.HSCROLL)
    editor.SetValue(model.controller.active.content if model.controller.active else content)
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
               "open_seq": 0, "open_applied": 0,
               "binary_refused": initial_binary_refused}
    try:
        note_disk_baseline(state, model.controller.active)
    except Exception:
        pass

    def notify_destroy():
        if on_destroy is not None and not state["destroy_notified"]:
            state["destroy_notified"] = True
            on_destroy(host)

    ctx = {"host": host, "model": model, "editor": editor, "doc_tabs": doc_tabs, "remote_path": remote_path, "status": status, "state": state, "save": save, "submit": submit, "run": run, "btn_open": btn_open, "btn_template": btn_template, "btn_lint": btn_lint, "action_factory": action_factory, "save_remote": save_remote, "on_submit": on_submit, "on_run": on_run, "on_open": on_open, "on_new_template": on_new_template, "on_lint": on_lint}

    def _label_fallback() -> str:
        return t("editor.title")

    def _update_dirty_marker():
        _update_dirty_marker_leaf(doc_tabs, model, _label_fallback())

    def _update_header_enabled():
        _update_header_enabled_leaf(ctx)

    ctx["update_header_enabled"] = _update_header_enabled

    def _wx_find_next() -> bool:
        return _find_next_leaf(editor, find_in, chk_match_case, status)

    def _wx_find_previous() -> bool:
        return _find_previous_leaf(editor, find_in, chk_match_case, status)

    def _wx_replace_current() -> bool:
        return _replace_current_leaf(editor, model, find_in, replace_in, chk_match_case, status, _update_dirty_marker)

    def _wx_replace_all() -> int:
        return _replace_all_leaf(editor, model, find_in, replace_in, chk_match_case, status, _update_dirty_marker)

    def save_document(mode="save", on_done=None):
        _save_document_leaf(ctx, mode, on_done)

    def _on_open(_event):
        on_open_action(ctx)

    def _on_template(_event):
        on_template_action(ctx)

    def _on_lint(_event):
        on_lint_action(ctx)

    def _on_remote_path_enter(_event):
        _on_open(_event)

    save.Bind(wx.EVT_BUTTON, lambda _event: save_document())
    submit.Bind(wx.EVT_BUTTON, lambda _event: save_document("submit"))
    run.Bind(wx.EVT_BUTTON, lambda _event: save_document("run"))
    btn_open.Bind(wx.EVT_BUTTON, _on_open)
    btn_template.Bind(wx.EVT_BUTTON, _on_template)
    btn_lint.Bind(wx.EVT_BUTTON, _on_lint)
    btn_find_next.Bind(wx.EVT_BUTTON, lambda _event: _wx_find_next())
    btn_find_prev.Bind(wx.EVT_BUTTON, lambda _event: _wx_find_previous())
    btn_replace.Bind(wx.EVT_BUTTON, lambda _event: _wx_replace_current())
    btn_replace_all.Bind(wx.EVT_BUTTON, lambda _event: _wx_replace_all())
    find_in.Bind(wx.EVT_TEXT_ENTER, lambda _event: _wx_find_next())
    replace_in.Bind(wx.EVT_TEXT_ENTER, lambda _event: _wx_replace_current())
    remote_path.Bind(wx.EVT_TEXT_ENTER, _on_remote_path_enter)
    _update_header_enabled()

    def _refresh_tabs():
        _refresh_tabs_leaf(doc_tabs, model, _label_fallback())

    def _on_tab_changed(event):
        _on_tab_changed_leaf(event, model, editor, remote_path, doc_tabs, host)

    def content_changed(event):
        if not state["in_flight"]:
            model.controller.update_content(editor.GetValue())
            _update_dirty_marker()
        event.Skip()

    editor.Bind(wx.EVT_TEXT, content_changed)
    try:
        doc_tabs.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, _on_tab_changed)
    except Exception:
        pass

    def _reorder_tabs(from_idx: int, to_idx: int):
        return _reorder_tabs_leaf(model, doc_tabs, _label_fallback(), from_idx, to_idx)

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
        try:
            find_label.SetLabel(t("editor.find_label"))
            find_in.SetHint(t("editor.find_placeholder"))
            replace_label.SetLabel(t("editor.replace_label"))
            replace_in.SetHint(t("editor.replace_placeholder"))
            btn_find_next.SetLabel(t("editor.find_next"))
            btn_find_prev.SetLabel(t("editor.find_previous"))
            chk_match_case.SetLabel(t("editor.match_case"))
            btn_replace.SetLabel(t("editor.replace"))
            btn_replace_all.SetLabel(t("editor.replace_all"))
        except Exception:
            pass
        _update_header_enabled()
        _refresh_tabs()

    def _begin_open_request() -> int:
        return begin_open_request(state)

    def load_document(new_path, new_content, *, is_local=False, provider="", profile="", session_key="", encoding="utf-8", newline=None, version="", request_seq=None):
        result = _load_document_leaf(model, editor, remote_path, doc_tabs, host, status, state, _label_fallback(), new_path, new_content, is_local=is_local, provider=provider, profile=profile, session_key=session_key, encoding=encoding, newline=newline, version=version, request_seq=request_seq)
        if result == "opened":
            _update_header_enabled()
        return result

    def save_for_replacement(callback):
        save_document(on_done=callback)

    def close_tab(index=None, *, force=False) -> bool:
        return _close_tab_leaf(model, editor, remote_path, doc_tabs, host, _label_fallback(), index, force=force)

    subscribe_language_change(refresh_labels)
    host.bind_host_close(close)
    if on_destroy is not None:
        def destroyed(event):
            unsubscribe_language_change(refresh_labels)
            notify_destroy()
            event.Skip()

        host.Bind(wx.EVT_WINDOW_DESTROY, destroyed)
    host._wx_editor_controls = {"editor": editor, "save": save, "submit": submit, "run": run, "status": status, "doc_tabs": doc_tabs, "find_in": find_in, "replace_in": replace_in, "find_next": btn_find_next, "find_prev": btn_find_prev, "match_case": chk_match_case, "replace": btn_replace, "replace_all": btn_replace_all, "find_label": find_label, "replace_label": replace_label}
    host._wx_editor_header = {"path": remote_path, "path_label": remote_label, "open": btn_open, "new_template": btn_template, "lint": btn_lint, "header": header, "doc_tabs": doc_tabs, "remote_label": remote_label}
    host._wx_editor_state = state
    host._wx_editor_model = model
    host._wx_editor_load_document = load_document
    host._wx_editor_save_for_replacement = save_for_replacement
    host._wx_editor_close_tab = close_tab
    host._wx_editor_reorder_tabs = _reorder_tabs
    host._wx_editor_refresh_tabs = _refresh_tabs
    host._wx_editor_find_next = _wx_find_next
    host._wx_editor_find_previous = _wx_find_previous
    host._wx_editor_replace_current = _wx_replace_current
    host._wx_editor_replace_all = _wx_replace_all
    host._wx_editor_begin_open_request = _begin_open_request
    finish()
    return host


def build_editor_panel(parent, model: WxEditorModel | None = None, *, path: str = "", content: str = "", is_local=None, save_remote=None, on_submit=None, on_run=None, action_factory=None, on_destroy=None, on_open=None, on_new_template=None, on_lint=None, provider: str = "", profile: str = "", session_key: str = "", encoding: str = "utf-8", newline: str | None = None, version: str = ""):
    """Embedded panel factory. Returns the wx.Panel host."""
    return _build_editor(parent, model, path=path, content=content, is_local=is_local, save_remote=save_remote, on_submit=on_submit, on_run=on_run, action_factory=action_factory, on_destroy=on_destroy, on_open=on_open, on_new_template=on_new_template, on_lint=on_lint, embedded=True, provider=provider, profile=profile, session_key=session_key, encoding=encoding, newline=newline, version=version)


def show_editor(parent=None, model: WxEditorModel | None = None, *, path: str = "", content: str = "", is_local=None, save_remote=None, on_submit=None, on_run=None, action_factory=None, on_destroy=None, on_open=None, on_new_template=None, on_lint=None, provider: str = "", profile: str = "", session_key: str = "", encoding: str = "utf-8", newline: str | None = None, version: str = ""):
    return _build_editor(parent, model, path=path, content=content, is_local=is_local, save_remote=save_remote, on_submit=on_submit, on_run=on_run, action_factory=action_factory, on_destroy=on_destroy, on_open=on_open, on_new_template=on_new_template, on_lint=on_lint, embedded=False, provider=provider, profile=profile, session_key=session_key, encoding=encoding, newline=newline, version=version)


__all__ = ["show_editor", "build_editor_panel", "editor_binary_guard_reason", "BINARY_GUARD_SIZE_BYTES"]

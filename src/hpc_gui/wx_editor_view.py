"""Native wx editor adapter for the framework-neutral editor model."""

from __future__ import annotations

from pathlib import Path
from threading import Thread

from hpc_gui.core.i18n import subscribe_language_change, t, unsubscribe_language_change
from hpc_gui.services.editor_controller import EditorCommandService
from hpc_gui.services.editor_controller import DocumentModel
from hpc_gui.wx_editor import WxEditorModel


def show_editor(parent=None, model: WxEditorModel | None = None, *, path: str = "", content: str = "", is_local=None, save_remote=None, on_submit=None, on_run=None, action_factory=None, on_destroy=None):
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    model = model or WxEditorModel()
    if model.controller.active is None:
        model.open(path, content, is_local=bool(path and Path(path).exists()) if is_local is None else is_local)
    frame = wx.Frame(parent, title=EditorCommandService.suggested_filename(path or "untitled.sh"), size=(900, 650))
    panel = wx.Panel(frame)
    root = wx.BoxSizer(wx.VERTICAL)
    editor = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_RICH2 | wx.HSCROLL)
    editor.SetValue(model.controller.active.content if model.controller.active else content)
    buttons = wx.BoxSizer(wx.HORIZONTAL)
    save = wx.Button(panel, label=t("editor.save"))
    submit = wx.Button(panel, label=t("editor.submit"))
    run = wx.Button(panel, label=t("editor.save_submit"))
    status = wx.StaticText(panel, label="")
    for button in (save, submit, run):
        buttons.Add(button, 0, wx.RIGHT, 6)
    root.Add(editor, 1, wx.EXPAND | wx.ALL, 8)
    root.Add(buttons, 0, wx.ALIGN_RIGHT | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
    root.Add(status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
    panel.SetSizer(root)
    state = {"closed": False, "in_flight": False, "destroy_notified": False}

    def notify_destroy():
        if on_destroy is not None and not state["destroy_notified"]:
            state["destroy_notified"] = True
            on_destroy(frame)

    def save_document(mode="save", on_done=None):
        if state["closed"] or state["in_flight"]:
            return
        active = model.controller.update_content(editor.GetValue())
        operation_callbacks = action_factory(active) if action_factory else None
        operation_save_remote = operation_callbacks["save_remote"] if operation_callbacks else save_remote
        operation_submit = operation_callbacks["on_submit"] if operation_callbacks else on_submit
        operation_run = operation_callbacks["on_run"] if operation_callbacks else on_run
        state["in_flight"] = True
        editor.Enable(False)
        for button in (save, submit, run):
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
            for button in (save, submit, run):
                button.Enable(True)
            if saved:
                model.controller.mark_saved(active.content)
            if error:
                status.SetLabel(str(error))
                return
            status.SetLabel("")
            if callback:
                callback()

        Thread(target=worker, daemon=True).start()

    save.Bind(wx.EVT_BUTTON, lambda _event: save_document())
    submit.Bind(wx.EVT_BUTTON, lambda _event: save_document("submit"))
    run.Bind(wx.EVT_BUTTON, lambda _event: save_document("run"))

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
                    frame.Destroy()

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
        save.SetLabel(t("editor.save"))
        submit.SetLabel(t("editor.submit"))
        run.SetLabel(t("editor.save_submit"))

    def load_document(new_path, new_content, *, is_local=False):
        model.controller.open(DocumentModel(new_path, new_content, new_content, is_local, suggested_filename=EditorCommandService.suggested_filename(new_path)))
        editor.SetValue(new_content)
        frame.SetTitle(EditorCommandService.suggested_filename(new_path or "untitled.sh"))

    def save_for_replacement(callback):
        save_document(on_done=callback)

    subscribe_language_change(refresh_labels)
    frame.Bind(wx.EVT_CLOSE, close)
    if on_destroy is not None:
        def destroyed(event):
            unsubscribe_language_change(refresh_labels)
            notify_destroy()
            event.Skip()

        frame.Bind(wx.EVT_WINDOW_DESTROY, destroyed)
    frame._wx_editor_controls = {"editor": editor, "save": save, "submit": submit, "run": run, "status": status}
    frame._wx_editor_state = state
    frame._wx_editor_model = model
    frame._wx_editor_load_document = load_document
    frame._wx_editor_save_for_replacement = save_for_replacement
    frame.Show()
    return frame


__all__ = ["show_editor"]

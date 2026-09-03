"""Native wx editor adapter for the framework-neutral editor model."""

from __future__ import annotations

from pathlib import Path
from threading import Thread

from hpc_gui.core.i18n import subscribe_language_change, t, unsubscribe_language_change
from hpc_gui.services.editor_controller import EditorCommandService
from hpc_gui.wx_editor import WxEditorModel


def show_editor(parent=None, model: WxEditorModel | None = None, *, path: str = "", content: str = "", save_remote=None, on_submit=None, on_run=None) -> int:
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    model = model or WxEditorModel()
    if model.controller.active is None:
        model.open(path, content, is_local=bool(path and Path(path).exists()))
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
    state = {"closed": False, "in_flight": False}

    def save_document(mode="save", on_done=None):
        if state["closed"] or state["in_flight"]:
            return
        active = model.controller.update_content(editor.GetValue())
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
                elif save_remote and snapshot.path:
                    save_remote(snapshot.path, snapshot.content)
                    saved = True
                if mode == "submit" and on_submit:
                    on_submit(snapshot)
                elif mode == "run" and on_run:
                    on_run(snapshot)
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
                    frame.Destroy()

                save_document(on_done=destroy_after_save)
                return
            state["closed"] = True
            unsubscribe_language_change(refresh_labels)
            event.Skip()

    def refresh_labels(_language=None):
        save.SetLabel(t("editor.save"))
        submit.SetLabel(t("editor.submit"))
        run.SetLabel(t("editor.save_submit"))

    subscribe_language_change(refresh_labels)
    frame.Bind(wx.EVT_CLOSE, close)
    frame._wx_editor_controls = {"editor": editor, "save": save, "submit": submit, "run": run, "status": status}
    frame._wx_editor_state = state
    frame.Show()
    return wx.ID_OK


__all__ = ["show_editor"]

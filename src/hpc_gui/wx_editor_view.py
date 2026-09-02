"""Native wx editor adapter for the framework-neutral editor model."""

from __future__ import annotations

from pathlib import Path

from hpc_gui.core.i18n import t
from hpc_gui.services.editor_controller import EditorCommandService
from hpc_gui.wx_editor import WxEditorModel


def show_editor(parent=None, model: WxEditorModel | None = None, *, path: str = "", content: str = "") -> int:
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
    for button in (save, submit, run):
        buttons.Add(button, 0, wx.RIGHT, 6)
    root.Add(editor, 1, wx.EXPAND | wx.ALL, 8)
    root.Add(buttons, 0, wx.ALIGN_RIGHT | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
    panel.SetSizer(root)

    def save_document(mode="save"):
        active = model.controller.update_content(editor.GetValue())
        if active.is_local and active.path:
            try:
                Path(active.path).write_text(active.content, encoding=active.encoding)
                model.controller.mark_saved()
            except OSError as error:
                wx.MessageBox(str(error), t("login.err_title"), wx.OK | wx.ICON_ERROR)
        elif mode == "submit":
            model.save_target(submit=True)
        elif mode == "run":
            model.save_target(run=True)

    save.Bind(wx.EVT_BUTTON, lambda _event: save_document())
    submit.Bind(wx.EVT_BUTTON, lambda _event: save_document("submit"))
    run.Bind(wx.EVT_BUTTON, lambda _event: save_document("run"))

    def close(event):
        if model.controller.active and model.controller.active.dirty:
            choice = wx.MessageBox(t("common.save_changes"), t("tabs.editor"), wx.YES_NO | wx.CANCEL | wx.ICON_WARNING)
            if choice == wx.CANCEL:
                return
            if choice == wx.YES:
                save_document()
        event.Skip()

    frame.Bind(wx.EVT_CLOSE, close)
    frame.Show()
    return wx.ID_OK


__all__ = ["show_editor"]

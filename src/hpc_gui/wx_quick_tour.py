"""Native wx guided tour with page navigation and persisted opt-out."""
from __future__ import annotations

from hpc_gui.config.storage import set_ui_pref_bool
from hpc_gui.core.i18n import t
from hpc_gui.core.platform import current_os
from hpc_gui.services.shortcut_preferences import active_binding


def tour_steps():
    def binding(command):
        return active_binding(command, current_os()) or t("help.unbound_command")

    return (
        ("NAV-DIRECTORIES", t("tour.s2_title"), t("tour.s2_body").format(binding=binding("FILE-NEW-FOLDER"))),
        ("NAV-DIRECTORIES", t("tour.s3_title"), t("tour.s3_body")),
        ("NAV-EDITOR", t("tour.s4_title"), t("tour.s4_body").format(binding=binding("EDIT-EXECUTE"))),
        ("NAV-LOGS", t("tour.s5_title"), t("tour.s5_body")),
    )


def show_quick_tour(parent):
    """Show one modeless guide per shell; the shell remains usable."""
    import wx

    if parent is None or parent.IsBeingDeleted():
        return None
    old = getattr(parent, "_wx_quick_tour", None)
    if old:
        try:
            if not old.IsBeingDeleted():
                old.Raise()
                return old
        except RuntimeError:
            pass

    dialog = wx.Dialog(parent, title=t("menu.quick_tour"),
                       style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
    parent._wx_quick_tour = dialog
    index = 0
    title = wx.StaticText(dialog)
    font = title.GetFont()
    font.SetWeight(wx.FONTWEIGHT_BOLD)
    title.SetFont(font)
    body = wx.StaticText(dialog)
    count = wx.StaticText(dialog)
    opt_out = wx.CheckBox(dialog, label=t("help.dont_show_again"))
    previous = wx.Button(dialog, label=t("tour.prev"))
    following = wx.Button(dialog, label=t("tour.next"))
    skip = wx.Button(dialog, label=t("tour.skip"))
    layout = wx.BoxSizer(wx.VERTICAL)
    for control in (title, body, count, opt_out):
        layout.Add(control, 0, wx.EXPAND | wx.ALL, 8)
    row = wx.BoxSizer(wx.HORIZONTAL)
    for control in (previous, following, skip):
        row.Add(control, 0, wx.ALL, 4)
    layout.Add(row, 0, wx.ALIGN_RIGHT | wx.ALL, 4)
    dialog.SetSizer(layout)

    def refresh():
        page_id, heading, message = tour_steps()[index]
        title.SetLabel(heading)
        body.SetLabel(message)
        body.Wrap(420)
        count.SetLabel(f"{index + 1}/{len(tour_steps())}")
        previous.Enable(index > 0)
        following.SetLabel(t("tour.finish" if index == len(tour_steps()) - 1 else "tour.next"))
        controls = getattr(parent, "_wx_shell_controls", {}) or {}
        notebook = controls.get("notebook")
        page = (controls.get("pages") or {}).get(page_id, {}).get("page")
        if notebook is not None and page is not None:
            target = notebook.FindPage(page)
            if target >= 0:
                notebook.SetSelection(target)
        dialog.Layout()
        dialog.Fit()

    def close(_event=None):
        try:
            if opt_out.GetValue():
                set_ui_pref_bool("show_tour", False)
        finally:
            if getattr(parent, "_wx_quick_tour", None) is dialog:
                parent._wx_quick_tour = None
            dialog.Destroy()

    def next_step(_event):
        nonlocal index
        if index == len(tour_steps()) - 1:
            close()
        else:
            index += 1
            refresh()

    def prev_step(_event):
        nonlocal index
        if index:
            index -= 1
            refresh()

    previous.Bind(wx.EVT_BUTTON, prev_step)
    following.Bind(wx.EVT_BUTTON, next_step)
    skip.Bind(wx.EVT_BUTTON, close)
    dialog.Bind(wx.EVT_CLOSE, close)
    dialog._wx_tour_controls = {
        "title": title, "body": body, "count": count, "opt_out": opt_out,
        "previous": previous, "next": following, "skip": skip,
    }
    refresh()
    dialog.CentreOnParent()
    dialog.Show()
    return dialog

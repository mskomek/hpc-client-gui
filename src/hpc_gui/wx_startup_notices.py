"""Native wx first-run and version-change notices, independent of the Qt UI."""
from __future__ import annotations

import logging

from hpc_gui import __version__
from hpc_gui.config.storage import (
    get_last_seen_changelog_version, get_ui_pref_bool,
    set_last_seen_changelog_version, set_ui_pref_bool,
)
from hpc_gui.core.i18n import current_language, t
from hpc_gui.core.resources import read_doc_text
from hpc_gui.services.changelog import chronological_changelog, load_changelog_text


def welcome_text() -> str:
    language = current_language()
    return (
        read_doc_text(f"WELCOME_{language}.md")
        or read_doc_text(f"HELP_{language}.md")
        or read_doc_text("WELCOME_en.md")
        or t("help.missing_help_text")
    )


def create_startup_notice(parent, title, text, *, allow_opt_out=False):
    """Read-only local documentation; no external document navigation."""
    import wx

    dialog = wx.Dialog(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
    from hpc_gui.wx_debug_telemetry import install_optional_window_telemetry

    install_optional_window_telemetry(dialog)
    layout = wx.BoxSizer(wx.VERTICAL)
    content = wx.TextCtrl(dialog, value=text, style=wx.TE_MULTILINE | wx.TE_READONLY)
    content.SetInsertionPoint(0)
    layout.Add(content, 1, wx.EXPAND | wx.ALL, 12)
    row = wx.BoxSizer(wx.HORIZONTAL)
    checkbox = None
    if allow_opt_out:
        checkbox = wx.CheckBox(dialog, label=t("help.dont_show_again"))
        row.Add(checkbox, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
    row.AddStretchSpacer()
    close = wx.Button(dialog, wx.ID_OK, t("common.close"))
    close.SetDefault()
    row.Add(close)
    layout.Add(row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
    dialog.SetSizer(layout)
    dialog.SetSize((720, 520))
    dialog.CentreOnParent()
    dialog._wx_startup_notice_controls = {"content": content, "opt_out": checkbox, "close": close}
    return dialog


def _present(parent, title, text, *, allow_opt_out=False) -> bool:
    import wx

    dialog = create_startup_notice(parent, title, text, allow_opt_out=allow_opt_out)
    try:
        result = dialog.ShowModal()
        checkbox = dialog._wx_startup_notice_controls["opt_out"]
        return bool(result == wx.ID_OK and checkbox is not None and checkbox.GetValue())
    finally:
        dialog.Destroy()


def show_startup_notices(parent, *, present=None) -> None:
    """Show the version changelog once and honor the persistent welcome choice.

    Only the normal desktop startup calls this function. Never record a
    changelog as seen when loading or presenting it failed.
    """
    log = logging.getLogger("hpc_gui.startup")
    present = present or _present

    def alive():
        try:
            return parent is not None and bool(parent) and not parent.IsBeingDeleted()
        except (AttributeError, RuntimeError):
            return False

    if not alive():
        return
    try:
        if get_last_seen_changelog_version() != __version__:
            text = chronological_changelog(load_changelog_text())
            if text:
                present(parent, t("updates.changelog_title").format(version=__version__), text)
            set_last_seen_changelog_version(__version__)
    except Exception:
        log.exception("Could not show or remember the startup changelog")
    if not alive():
        return
    try:
        if get_ui_pref_bool("show_welcome", True):
            if present(parent, t("help.welcome_title"), welcome_text(), allow_opt_out=True):
                set_ui_pref_bool("show_welcome", False)
    except Exception:
        log.exception("Could not show or remember the welcome notice")

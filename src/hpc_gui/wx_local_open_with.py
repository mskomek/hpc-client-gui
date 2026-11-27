"""wx action for opening a local file with a chosen application."""

from __future__ import annotations

import subprocess
from pathlib import Path

from hpc_gui.config.storage import get_file_association, set_file_association
from hpc_gui.core.i18n import t


def open_local_with_program(wx, parent, path: str | Path) -> bool:
    """Launch a chosen program and optionally remember it for the extension."""
    target = Path(path)
    if not target.is_file():
        return False

    program = get_file_association(target.suffix)
    if not program or not Path(program).is_file():
        dialog = wx.FileDialog(
            parent,
            t("files.open_with_select_program"),
            wildcard=t("files.open_with_program_filter"),
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        )
        try:
            if dialog.ShowModal() != wx.ID_OK:
                return False
            program = str(dialog.GetPath() or "").strip()
        finally:
            dialog.Destroy()
        if not program:
            return False
        if target.suffix:
            answer = wx.MessageBox(
                t("files.open_with_save_prompt").format(
                    extension=target.suffix.lower()
                ),
                t("files.open_with_save_title"),
                wx.YES_NO | wx.ICON_QUESTION,
                parent,
            )
            if answer == wx.YES:
                set_file_association(target.suffix, program)

    try:
        subprocess.Popen([program, str(target)])
    except OSError as error:
        wx.MessageBox(
            str(error), t("common.error"), wx.OK | wx.ICON_ERROR, parent
        )
        return False
    return True

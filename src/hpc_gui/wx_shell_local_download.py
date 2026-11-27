"""Local file-browser callbacks for downloading remote selections."""

from __future__ import annotations

from threading import Thread

from hpc_gui.core.i18n import t
from hpc_gui.wx_shell_download import prepare_download
from hpc_gui.wx_shell_file_transfer import _start_file_transfers


def build_remote_download_callback(session_state, parent, lifecycle):
    """Build the local browser's remote-to-local transfer callback."""

    def download_remote(paths, destination):
        session = (session_state or {}).get("session") or {}
        files = session.get("files")
        if not files:
            return
        generation = session_state.get("generation")

        def worker():
            try:
                prepare_download(
                    session_state,
                    lifecycle,
                    parent,
                    session,
                    files,
                    tuple(paths),
                    destination,
                    _start_file_transfers,
                    generation=generation,
                )
            except Exception as error:
                import wx

                wx.CallAfter(
                    wx.MessageBox,
                    str(error),
                    t("login.err_title"),
                    wx.OK | wx.ICON_ERROR,
                    parent,
                )

        Thread(target=worker, daemon=True).start()

    return download_remote

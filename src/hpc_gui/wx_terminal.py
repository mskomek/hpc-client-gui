"""wx-compatible terminal model and optional text adapter."""

from __future__ import annotations


from hpc_gui.core.i18n import subscribe_language_change, t, unsubscribe_language_change


from hpc_gui.wx_terminal_model import TerminalModel, TerminalSize


def build_terminal_panel(
    parent, *, model: TerminalModel | None = None, ssh=None, send_input=None,
    resize_pty=None, lifecycle=None
):
    """Build the preferred WebView renderer, then the compatible TextCtrl fallback."""
    try:
        from hpc_gui.wx_terminal_webview import build_terminal_panel as build_webview

        return build_webview(
            parent, model=model, ssh=ssh, send_input=send_input,
            resize_pty=resize_pty, lifecycle=lifecycle
        )
    except Exception:
        from hpc_gui.wx_terminal_text import build_text_terminal_panel

        return build_text_terminal_panel(
            parent, model=model, ssh=ssh, send_input=send_input,
            resize_pty=resize_pty, lifecycle=lifecycle
        )


def show_terminal(parent=None, send_input=None, resize_pty=None, *, ssh=None, lifecycle=None) -> int:
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    if ssh is None and send_input is None:
        wx.MessageBox(t("login.status_disconnected"), t("login.err_title"), wx.OK | wx.ICON_WARNING)
        return wx.ID_CANCEL
    if ssh is not None:
        send_input = getattr(ssh, "send_shell_input", send_input)
        resize_pty = getattr(ssh, "resize_shell_pty", resize_pty)
    model = TerminalModel(send_input, resize_pty)
    frame = wx.Frame(parent, title=t("help.section_terminal"), size=(900, 600))
    frame._terminal_model = model
    panel = build_terminal_panel(frame, model=model, ssh=ssh, lifecycle=lifecycle)
    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(panel, 1, wx.EXPAND)
    frame.SetSizer(sizer)
    # panel already handles i18n, font, find/clear, PTY; frame just delegates title and cleanup
    def refresh_labels(_language=None):
        frame.SetTitle(t("help.section_terminal"))
    subscribe_language_change(refresh_labels)
    def close(_event=None):
        try:
            panel._wx_terminal_close()
        except Exception:
            pass
        try:
            unsubscribe_language_change(refresh_labels)
        except Exception:
            pass
        frame.Destroy()
    frame.Bind(wx.EVT_CLOSE, close)
    frame._wx_terminal_panel = panel
    frame._wx_terminal_controls = panel._wx_terminal_controls
    if lifecycle is not None:
        lifecycle.register_cleanup(close)
    frame.Show()
    return wx.ID_OK


__all__ = ["TerminalModel", "TerminalSize", "build_terminal_panel", "show_terminal"]

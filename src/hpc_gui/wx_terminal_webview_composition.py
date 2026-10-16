"""Composition entry points for embedded and detached wx WebView terminals."""

from hpc_gui.core.i18n import subscribe_language_change, t, unsubscribe_language_change
from hpc_gui.wx_terminal_webview import WxTerminalWebViewPanel, _is_webview_available


def build_terminal_panel(parent, *, model=None, ssh=None, send_input=None, resize_pty=None, lifecycle=None):
    """Public composition entry — tries WebView, falls back to diagnostic non-parity panel.

    Keeps literal references to ssh.send_shell_input / ssh.resize_shell_pty for test seam.
    """
    # Keep model param for compat but ignore for WebView (xterm is authority)
    # If WebView is available, use it; else fall back to TextCtrl via wx_terminal
    if _is_webview_available():
        try:
            panel = WxTerminalWebViewPanel(parent, ssh=ssh, send_input=send_input, resize_pty=resize_pty, lifecycle=lifecycle)
            # Expose same seam as old panel for shell compatibility
            panel._terminal_model = model  # for compat
            panel._terminal_ssh = ssh
            panel._wx_terminal_close = panel.close
            panel._wx_terminal_set_ssh = panel.set_ssh
            # For tests that call _wx_terminal_render, provide a wrapper that writes to xterm
            def _render_wrap(data):
                panel.hpc_write(data)

            panel._wx_terminal_render = _render_wrap
            # Expose model getter for old tests (may be None)
            if model is not None:
                panel._wx_terminal_model = model
            else:
                # Create a minimal model-like object for compat (clear/find/font)
                class _CompatModel:
                    def __init__(self, panel):
                        self._panel = panel
                        self.text = ""  # not used for rendering, but for find
                        self.font_size = panel._font_size

                    def receive(self, data):
                        self.text += str(data or "")
                        # Do not splitlines — preserve for find
                        if len(self.text) > 50000:
                            self.text = self.text[-50000:]

                    def find(self, q):
                        return self.text.find(q) if q else -1

                    def clear(self):
                        self.text = ""
                        self._panel.hpc_clear()

                    def change_font_size(self, delta):
                        self._panel._change_font(delta)
                        self.font_size = self._panel._font_size
                        return self.font_size

                compat = _CompatModel(panel)
                panel._wx_terminal_model = compat

            return panel
        except Exception:
            # Fall through to TextCtrl fallback
            pass

    # Fallback — import legacy TextCtrl panel (non-parity, diagnostic)
    try:
        from hpc_gui.wx_terminal import build_terminal_panel as _legacy_build
    except Exception as exc:
        raise RuntimeError("wx terminal fallback unavailable") from exc
    # Legacy panel already handles ssh/send_input/resize_pty/lifecycle
    panel = _legacy_build(parent, model=model, ssh=ssh, send_input=send_input, resize_pty=resize_pty, lifecycle=lifecycle)
    # Mark as non-parity explicitly
    try:
        panel._wx_terminal_is_webview = False  # type: ignore
        panel._wx_terminal_is_parity = False  # type: ignore
    except Exception:
        pass
    return panel


def show_terminal(parent=None, send_input=None, resize_pty=None, *, ssh=None, lifecycle=None) -> int:
    """Detached terminal — uses same WebView renderer, not TextCtrl divergence."""
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
    # Use lifecycle-aware frame
    frame = wx.Frame(parent, title=t("help.section_terminal"), size=(900, 600))
    panel = build_terminal_panel(frame, ssh=ssh, send_input=send_input, resize_pty=resize_pty, lifecycle=lifecycle)
    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(panel, 1, wx.EXPAND)
    frame.SetSizer(sizer)

    def refresh_labels(_language=None):
        try:
            frame.SetTitle(t("help.section_terminal"))
        except Exception:
            pass

    subscribe_language_change(refresh_labels)

    def close(_event=None):
        try:
            # Panel close handles unsubscribe and timers
            c = getattr(panel, "_wx_terminal_close", None) or getattr(panel, "close", None)
            if callable(c):
                c()
        except Exception:
            pass
        try:
            unsubscribe_language_change(refresh_labels)
        except Exception:
            pass
        try:
            frame.Destroy()
        except Exception:
            pass

    frame.Bind(wx.EVT_CLOSE, close)
    frame._wx_terminal_panel = panel
    # Expose controls for tests
    try:
        frame._wx_terminal_controls = getattr(panel, "_wx_terminal_controls", {})
    except Exception:
        frame._wx_terminal_controls = {}
    if lifecycle is not None:
        lifecycle.register_cleanup(close)
    frame.Show()
    return wx.ID_OK



"""Bridge xterm clipboard shortcuts to the native system clipboard."""

from __future__ import annotations

CLIPBOARD_COPY_PREFIX = "\x00HPCGUI_CLIPBOARD_COPY\x00"
CLIPBOARD_PASTE_REQUEST = "\x00HPCGUI_CLIPBOARD_PASTE\x00"
CLIPBOARD_ESCAPE_PREFIX = "\x00HPCGUI_CLIPBOARD_ESC\x00"


def install_terminal_clipboard_shortcuts(panel, wx_module=None) -> None:
    """Handle clipboard control messages without sending them to the cluster."""
    if wx_module is None:
        import wx as wx_module

    original = panel._handle_input

    def copy_to_clipboard(value: str) -> bool:
        opened = False
        try:
            opened = bool(wx_module.TheClipboard.Open())
            if not opened:
                return False
            return bool(wx_module.TheClipboard.SetData(wx_module.TextDataObject(value)))
        except Exception:
            return False
        finally:
            if opened:
                try:
                    wx_module.TheClipboard.Close()
                except Exception:
                    pass

    def paste_from_clipboard() -> bool:
        opened = False
        try:
            opened = bool(wx_module.TheClipboard.Open())
            if not opened:
                return False
            value = wx_module.TextDataObject()
            if wx_module.TheClipboard.GetData(value):
                text = value.GetText()
                if text:
                    panel.hpc_paste(text)
            return True
        except Exception:
            return False
        finally:
            if opened:
                try:
                    wx_module.TheClipboard.Close()
                except Exception:
                    pass

    def handle_input(data: str) -> bool:
        if data == CLIPBOARD_PASTE_REQUEST:
            return paste_from_clipboard()
        if data.startswith(CLIPBOARD_COPY_PREFIX):
            return copy_to_clipboard(data[len(CLIPBOARD_COPY_PREFIX):])
        if data.startswith(CLIPBOARD_ESCAPE_PREFIX):
            return original(data[len(CLIPBOARD_ESCAPE_PREFIX):])
        return original(data)

    panel._handle_input = handle_input
    panel._wx_terminal_clipboard_input = handle_input

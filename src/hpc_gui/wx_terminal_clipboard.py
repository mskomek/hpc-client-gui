"""Bridge xterm clipboard shortcuts to the native system clipboard."""

from __future__ import annotations

from hpc_gui.services.system_clipboard import get_text, set_text

CLIPBOARD_COPY_PREFIX = "\x00HPCGUI_CLIPBOARD_COPY\x00"
CLIPBOARD_PASTE_REQUEST = "\x00HPCGUI_CLIPBOARD_PASTE\x00"
CLIPBOARD_ESCAPE_PREFIX = "\x00HPCGUI_CLIPBOARD_ESC\x00"


def install_terminal_clipboard_shortcuts(panel, wx_module=None) -> None:
    """Handle clipboard control messages without sending them to the cluster."""
    if wx_module is None:
        import wx as wx_module

    original = panel._handle_input

    def copy_to_clipboard(value: str) -> bool:
        return set_text(wx_module.TheClipboard, wx_module.TextDataObject, value)

    def paste_from_clipboard() -> bool:
        text = get_text(wx_module.TheClipboard, wx_module.TextDataObject)
        if text is None:
            return False
        if text:
            panel.hpc_paste(text)
        return True

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

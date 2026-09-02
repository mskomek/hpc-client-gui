"""wx-compatible terminal model and optional text adapter."""

from __future__ import annotations

from dataclasses import dataclass

from hpc_gui.core.i18n import t


@dataclass(frozen=True)
class TerminalSize:
    columns: int
    rows: int


class TerminalModel:
    """Keep PTY semantics independent from the toolkit renderer."""

    def __init__(self, send_input=None, resize_pty=None) -> None:
        self._send_input = send_input
        self._resize_pty = resize_pty
        self.text = ""
        self.font_size = 11

    def receive(self, data: str) -> None:
        self.text += str(data or "")
        lines = self.text.splitlines()
        if len(lines) > 5000:
            self.text = "\n".join(lines[-5000:])

    def key_input(self, key: str, *, command: bool = False, shift: bool = False) -> str:
        if key == "C" and not shift and not command:
            payload = "\x03"
        elif key == "D" and not shift and not command:
            payload = "\x04"
        elif key == "Z" and not shift and not command:
            payload = "\x1a"
        elif key in {"C", "V"} and (command or shift):
            return "copy" if key == "C" else "paste"
        else:
            payload = key
        if self._send_input:
            self._send_input(payload)
        return payload

    def resize(self, width: int, height: int, char_width: int = 8, char_height: int = 18) -> TerminalSize:
        size = TerminalSize(max(1, width // max(1, char_width)), max(1, height // max(1, char_height)))
        if self._resize_pty:
            self._resize_pty(size.columns, size.rows)
        return size

    def find(self, query: str) -> int:
        return self.text.find(query) if query else -1

    def clear(self) -> None:
        self.text = ""

    def change_font_size(self, delta: int) -> int:
        self.font_size = max(6, min(32, self.font_size + int(delta)))
        return self.font_size


def show_terminal(parent=None, send_input=None, resize_pty=None, *, ssh=None) -> int:
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    if ssh is None and send_input is None:
        wx.MessageBox(t("login.status_disconnected"), t("login.err_title"), wx.OK | wx.ICON_WARNING)
        return wx.ID_CANCEL
    if ssh is not None:
        send_input = ssh.send_shell_input
        resize_pty = ssh.resize_shell_pty
    model = TerminalModel(send_input, resize_pty)
    frame = wx.Frame(parent, title="Terminal", size=(900, 600))
    frame._terminal_model = model
    text = wx.TextCtrl(frame, style=wx.TE_MULTILINE | wx.TE_RICH2 | wx.TE_PROCESS_TAB)
    text.SetFocus()
    def render_output(data):
        model.receive(data)
        text.ChangeValue("\n".join(model.text.splitlines()[-5000:]))
        text.ShowPosition(text.GetLastPosition())

    def key_event(event):
        keycode = event.GetKeyCode()
        if (event.CmdDown() or event.ControlDown()) and keycode in (ord("C"), ord("V")):
            if keycode == ord("V"):
                text.Paste()
            elif event.CmdDown() or event.ShiftDown():
                text.Copy()
            else:
                model.key_input("C")
            return
        key = event.GetUnicodeKey()
        if key == wx.WXK_NONE or not (32 <= key <= 126):
            key = event.GetKeyCode()
        if key in (3, 4, 26):
            key = {3: "C", 4: "D", 26: "Z"}[key]
        if isinstance(key, int) and key > 0:
            key = chr(key)
        if event.ControlDown() and str(key).upper() == "C" and event.ShiftDown():
            text.Copy()
        elif key:
            model.key_input(str(key), command=event.CmdDown(), shift=event.ShiftDown())
        else:
            event.Skip()

    text.Bind(wx.EVT_CHAR, key_event)
    subscriber = None
    if ssh is not None:
        subscribers = getattr(ssh, "_wx_output_subscribers", None)
        if subscribers is not None:
            def subscriber(data):
                wx.CallAfter(render_output, data)

            subscribers.append(subscriber)

    def close(_event):
        if subscriber is not None and subscribers is not None:
            try:
                subscribers.remove(subscriber)
            except ValueError:
                pass
        frame.Destroy()

    frame.Bind(wx.EVT_CLOSE, close)
    frame.Show()
    return wx.ID_OK


__all__ = ["TerminalModel", "TerminalSize", "show_terminal"]

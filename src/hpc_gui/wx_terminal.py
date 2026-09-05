"""wx-compatible terminal model and optional text adapter."""

from __future__ import annotations

from dataclasses import dataclass

from hpc_gui.core.i18n import subscribe_language_change, t, unsubscribe_language_change


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


def show_terminal(parent=None, send_input=None, resize_pty=None, *, ssh=None, lifecycle=None) -> int:
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
    frame = wx.Frame(parent, title=t("help.section_terminal"), size=(900, 600))
    frame._terminal_model = model
    panel = wx.Panel(frame)
    root = wx.BoxSizer(wx.VERTICAL)
    # Toolbar: Find + Clear + Font A-/A+
    toolbar = wx.BoxSizer(wx.HORIZONTAL)
    find_ctrl = wx.TextCtrl(panel, value="", style=wx.TE_PROCESS_ENTER)
    find_ctrl.SetHint(t("login.terminal_find") if t("login.terminal_find") != "[login.terminal_find]" else "Find")
    find_btn = wx.Button(panel, label=t("login.terminal_find"))
    clear_btn = wx.Button(panel, label=t("login.terminal_clear"))
    font_down_btn = wx.Button(panel, label=t("login.terminal_font_decrease_short"))
    font_up_btn = wx.Button(panel, label=t("login.terminal_font_increase_short"))
    find_btn.SetToolTip(t("login.terminal_find"))
    clear_btn.SetToolTip(t("login.terminal_clear"))
    font_down_btn.SetToolTip(t("login.terminal_font_decrease"))
    font_up_btn.SetToolTip(t("login.terminal_font_increase"))
    toolbar.Add(find_ctrl, 1, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
    toolbar.Add(find_btn, 0, wx.RIGHT, 6)
    toolbar.Add(clear_btn, 0, wx.RIGHT, 6)
    toolbar.Add(font_down_btn, 0, wx.RIGHT, 4)
    toolbar.Add(font_up_btn, 0)
    root.Add(toolbar, 0, wx.EXPAND | wx.ALL, 6)
    text = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_RICH2 | wx.TE_PROCESS_TAB)
    root.Add(text, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)
    panel.SetSizer(root)
    text.SetFocus()

    def apply_font():
        try:
            font = text.GetFont()
            font.SetPointSize(max(6, min(32, int(model.font_size))))
            text.SetFont(font)
            text.Refresh()
        except Exception:
            pass

    def do_find(_evt=None):
        query = find_ctrl.GetValue()
        pos = model.find(query)
        if pos >= 0:
            text.SetInsertionPoint(pos)
            try:
                text.SetSelection(pos, pos + len(query))
            except Exception:
                pass
            text.SetFocus()
            text.ShowPosition(pos)

    def do_clear(_evt=None):
        model.clear()
        text.Clear()
        text.ChangeValue("")

    def do_font(delta):
        def handler(_evt=None):
            model.change_font_size(delta)
            apply_font()
        return handler

    find_btn.Bind(wx.EVT_BUTTON, do_find)
    find_ctrl.Bind(wx.EVT_TEXT_ENTER, do_find)
    clear_btn.Bind(wx.EVT_BUTTON, do_clear)
    font_down_btn.Bind(wx.EVT_BUTTON, do_font(-1))
    font_up_btn.Bind(wx.EVT_BUTTON, do_font(1))

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

    closed = False
    def refresh_labels(_language=None):
        frame.SetTitle(t("help.section_terminal"))
        try:
            find_ctrl.SetHint(t("login.terminal_find"))
            find_btn.SetLabel(t("login.terminal_find"))
            clear_btn.SetLabel(t("login.terminal_clear"))
            clear_btn.SetToolTip(t("login.terminal_clear"))
            font_down_btn.SetLabel(t("login.terminal_font_decrease_short"))
            font_down_btn.SetToolTip(t("login.terminal_font_decrease"))
            font_up_btn.SetLabel(t("login.terminal_font_increase_short"))
            font_up_btn.SetToolTip(t("login.terminal_font_increase"))
            find_btn.SetToolTip(t("login.terminal_find"))
        except Exception:
            pass

    def close(_event=None):
        nonlocal closed
        if closed:
            return
        closed = True
        if subscriber is not None and subscribers is not None:
            try:
                subscribers.remove(subscriber)
            except ValueError:
                pass
        unsubscribe_language_change(refresh_labels)
        frame.Destroy()

    frame._wx_terminal_controls = {"find": find_ctrl, "find_btn": find_btn, "clear": clear_btn, "font_down": font_down_btn, "font_up": font_up_btn, "output": text}
    frame.Bind(wx.EVT_CLOSE, close)
    subscribe_language_change(refresh_labels)
    if lifecycle is not None:
        lifecycle.register_cleanup(close)
    apply_font()
    frame.Show()
    return wx.ID_OK


__all__ = ["TerminalModel", "TerminalSize", "show_terminal"]

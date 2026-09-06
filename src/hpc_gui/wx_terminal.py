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


def build_terminal_panel(parent, *, model: TerminalModel | None = None, ssh=None, send_input=None, resize_pty=None, lifecycle=None):
    """Reusable terminal panel for both embedded and detached use."""
    # keep literal references for optional ssh renderer contract
    # ssh.send_shell_input / ssh.resize_shell_pty
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    if ssh is not None:
        send_input = getattr(ssh, "send_shell_input", send_input)
        resize_pty = getattr(ssh, "resize_shell_pty", resize_pty)
    model = model or TerminalModel(send_input, resize_pty)
    # allow caller to pass model without ssh; resolve ssh callbacks if still None
    if ssh is not None and model._send_input is None:
        model._send_input = getattr(ssh, "send_shell_input", None)
        model._resize_pty = getattr(ssh, "resize_shell_pty", None)
    panel = wx.Panel(parent)
    panel._terminal_model = model
    panel._terminal_ssh = ssh
    root = wx.BoxSizer(wx.VERTICAL)
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

    # resize -> PTY
    def on_size(_evt):
        try:
            size = panel.GetClientSize()
            model.resize(size.width, size.height)
        except Exception:
            pass
        _evt.Skip()
    panel.Bind(wx.EVT_SIZE, on_size)

    subscriber = None
    subscribers = getattr(ssh, "_wx_output_subscribers", None) if ssh is not None else None
    if subscribers is not None:
        def subscriber(data):
            try:
                import wx as _wx2
                _wx2.CallAfter(render_output, data)
            except Exception:
                pass
        subscribers.append(subscriber)

    closed = {"v": False}
    def refresh_labels(_language=None):
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

    def close():
        if closed["v"]:
            return
        closed["v"] = True
        if subscriber is not None and subscribers is not None:
            try:
                subscribers.remove(subscriber)
            except ValueError:
                pass
        try:
            unsubscribe_language_change(refresh_labels)
        except Exception:
            pass

    def set_ssh(new_ssh):
        # swap underlying PTY callbacks; keep same model/text so find/clear persist
        panel._terminal_ssh = new_ssh
        if new_ssh is not None:
            model._send_input = getattr(new_ssh, "send_shell_input", model._send_input)
            model._resize_pty = getattr(new_ssh, "resize_shell_pty", model._resize_pty)
            # re-subscribe
            subs = getattr(new_ssh, "_wx_output_subscribers", None)
            if subs is not None:
                def new_sub(data):
                    try:
                        import wx as _wx3
                        _wx3.CallAfter(render_output, data)
                    except Exception:
                        pass
                # remove old if present
                if subscriber is not None and subscribers is not None:
                    try:
                        subscribers.remove(subscriber)
                    except Exception:
                        pass
                subs.append(new_sub)
                panel._terminal_subscriber = new_sub
                panel._terminal_subscribers = subs

    # Spec §69-71: terminal canvas uses single TextCtrl for both output and input; expose both keys for test seam
    panel._wx_terminal_controls = {"find": find_ctrl, "find_btn": find_btn, "clear": clear_btn, "font_down": font_down_btn, "font_up": font_up_btn, "output": text, "input": text, "model": model}
    panel._wx_terminal_close = close
    panel._wx_terminal_set_ssh = set_ssh
    panel._wx_terminal_render = render_output
    panel._wx_terminal_model = model
    subscribe_language_change(refresh_labels)
    if lifecycle is not None:
        lifecycle.register_cleanup(close)
    apply_font()
    # keep reference for shell to call close on detach
    panel.Bind(wx.EVT_WINDOW_DESTROY, lambda e: close() or e.Skip())
    return panel


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

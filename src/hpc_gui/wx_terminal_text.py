"""Legacy wx.TextCtrl terminal surface used when WebView is unavailable."""

from __future__ import annotations

from hpc_gui.core.i18n import subscribe_language_change, t, unsubscribe_language_change
from hpc_gui.wx_terminal_model import TerminalModel


def build_text_terminal_panel(
    parent, *, model: TerminalModel | None = None, ssh=None, send_input=None,
    resize_pty=None, lifecycle=None
):
    """Create the accessible TextCtrl fallback and preserve its lifecycle hooks."""
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
    find_ctrl.SetHint(t("login.terminal_find"))
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
            text.SetFocus()
            text.SetInsertionPoint(pos)

            def select_match():
                try:
                    if text.IsBeingDeleted():
                        return
                    if text.GetValue()[pos:pos + len(query)] != query:
                        return
                    # GTK can deliver a delayed focus event that collapses a
                    # synchronous selection. Apply scrolling and selection
                    # after the native focus transition has settled.
                    text.ShowPosition(pos)
                    text.SetSelection(pos, pos + len(query))
                except Exception:
                    pass

            wx.CallAfter(select_match)

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

    closed = {"v": False}
    # Generation guard mirroring the WebView path (LIFE-066/068): every
    # close/reconnect mints a fresh generation so already-queued output from
    # the previous session is dropped instead of rendering into the new one.
    generation = {"v": 0}

    def render_output(data, _gen=None):
        # Lifecycle guard mirroring the WebView path (LIFE-066/068):
        # output queued before close/reconnect must neither touch a dead
        # control nor render stale bytes into the superseded view.
        if closed["v"]:
            return
        if _gen is not None and _gen != generation["v"]:
            return
        try:
            if text.IsBeingDeleted():
                return
        except Exception:
            pass
        model.receive(data)
        text.ChangeValue("\n".join(model.text.splitlines()[-5000:]))
        text.ShowPosition(text.GetLastPosition())

    def key_event(event):
        keycode = event.GetKeyCode()
        if (event.CmdDown() or event.ControlDown()) and keycode in (ord("C"), ord("V")):
            if keycode == ord("V"):
                if wx.TheClipboard.Open():
                    try:
                        clipboard = wx.TextDataObject()
                        if wx.TheClipboard.GetData(clipboard):
                            model.key_input(
                                clipboard.GetText().replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\r")
                            )
                    finally:
                        wx.TheClipboard.Close()
            elif event.CmdDown() or event.ShiftDown():
                text.Copy()
            else:
                model.key_input("C")
            return
        special = {
            wx.WXK_UP: "\x1b[A",
            wx.WXK_DOWN: "\x1b[B",
            wx.WXK_RIGHT: "\x1b[C",
            wx.WXK_LEFT: "\x1b[D",
            wx.WXK_HOME: "\x1b[H",
            wx.WXK_END: "\x1b[F",
            wx.WXK_DELETE: "\x1b[3~",
            wx.WXK_INSERT: "\x1b[2~",
            wx.WXK_PAGEUP: "\x1b[5~",
            wx.WXK_PAGEDOWN: "\x1b[6~",
            wx.WXK_BACK: "\x7f",
            wx.WXK_RETURN: "\r",
            wx.WXK_NUMPAD_ENTER: "\r",
            wx.WXK_TAB: "\x1b[Z" if event.ShiftDown() else "\t",
            wx.WXK_ESCAPE: "\x1b",
        }
        if keycode in special:
            model.key_input(special[keycode])
            return
        key = event.GetUnicodeKey()
        if key == wx.WXK_NONE:
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
    # Keep ownership of every transport subscription made by this panel.  A
    # reconnect replaces the callback and transport, so removing only the
    # original closure would leak callbacks on intermediate sessions.
    subscription_refs = []
    subscribers = getattr(ssh, "_wx_output_subscribers", None) if ssh is not None else None
    if subscribers is not None:
        # Pin the subscription-time generation: output queued under the old
        # session must be dropped after a reconnect mints a new one.
        _sub_gen = generation["v"]

        def subscriber(data, _gen=_sub_gen):
            try:
                import wx as _wx2
                _wx2.CallAfter(render_output, data, _gen)
            except Exception:
                pass
        subscribers.append(subscriber)
        subscription_refs.append((subscribers, subscriber))

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
        # Mint a fresh generation so already-queued output can no longer
        # render into the closed view.
        generation["v"] += 1
        for registered_subscribers, registered_callback in subscription_refs:
            try:
                registered_subscribers.remove(registered_callback)
            except (ValueError, AttributeError):
                pass
        subscription_refs.clear()
        try:
            unsubscribe_language_change(refresh_labels)
        except Exception:
            pass

    def set_ssh(new_ssh):
        # swap underlying PTY callbacks; keep same model/text so find/clear persist
        panel._terminal_ssh = new_ssh
        # Every swap mints a fresh generation: output queued under the old
        # session must not render into the new one (LIFE-066 stale-output).
        generation["v"] += 1
        if new_ssh is None:
            # Disconnected: neutralize the write path so keystrokes can no
            # longer reach the dead transport (CONN-020), and detach the
            # previous session's output subscriber so late output cannot
            # render into the disconnected view (RECON-006).
            model._send_input = None
            model._resize_pty = None
            for registered_subscribers, registered_callback in subscription_refs:
                try:
                    registered_subscribers.remove(registered_callback)
                except (ValueError, AttributeError):
                    pass
            subscription_refs.clear()
            panel._terminal_subscriber = None
            return
        if new_ssh is not None:
            model._send_input = getattr(new_ssh, "send_shell_input", model._send_input)
            model._resize_pty = getattr(new_ssh, "resize_shell_pty", model._resize_pty)
            # re-subscribe
            subs = getattr(new_ssh, "_wx_output_subscribers", None)
            if subs is not None:
                _new_gen = generation["v"]
                def new_sub(data, _gen=_new_gen):
                    try:
                        import wx as _wx3
                        _wx3.CallAfter(render_output, data, _gen)
                    except Exception:
                        pass
                # Remove every callback owned by this panel before attaching
                # the replacement, including callbacks from prior swaps.
                for registered_subscribers, registered_callback in subscription_refs:
                    try:
                        registered_subscribers.remove(registered_callback)
                    except (ValueError, AttributeError):
                        pass
                subscription_refs.clear()
                subs.append(new_sub)
                subscription_refs.append((subs, new_sub))
                panel._terminal_subscriber = new_sub
                panel._terminal_subscribers = subs

    # Spec §69-71: terminal canvas uses single TextCtrl for both output and input; expose both keys for test seam
    panel._wx_terminal_controls = {"find": find_ctrl, "find_btn": find_btn, "clear": clear_btn, "font_down": font_down_btn, "font_up": font_up_btn, "output": text, "input": text, "model": model}
    panel._wx_terminal_close = close
    panel._wx_terminal_set_ssh = set_ssh

    def render_guarded(data):
        # Direct renders target the current generation; post-close renders
        # are dropped by the closed guard inside render_output.
        render_output(data)

    panel._wx_terminal_render = render_guarded
    panel._wx_terminal_model = model
    subscribe_language_change(refresh_labels)
    if lifecycle is not None:
        lifecycle.register_cleanup(close)
    apply_font()
    # keep reference for shell to call close on detach
    panel.Bind(wx.EVT_WINDOW_DESTROY, lambda e: close() or e.Skip())
    return panel



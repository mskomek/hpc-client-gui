"""Small wx progress control with a red-to-green connection gradient."""

from __future__ import annotations


class ConnectionProgressView:
    """Own the visible stage text, event log, and gradient progress bar."""

    def __init__(self, wx, parent, root) -> None:
        self.wx = wx
        self.history: list[str] = []
        self.value = 0
        self.stage = wx.StaticText(parent, label=self._text("connection.progress_idle"))
        self.stage.SetForegroundColour(wx.Colour(90, 90, 90))
        self.bar = self._create_bar(parent)
        self.log = wx.TextCtrl(
            parent,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2,
            size=wx.Size(-1, 64),
        )
        self.log.SetMinSize(wx.Size(-1, 64))
        self.log.SetName("ConnectionProgressLog")
        root.Add(self.stage, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)
        root.Add(self.bar, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 5)
        root.Add(self.log, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 5)

    def _text(self, key: str) -> str:
        from hpc_gui.core.i18n import t

        value = t(key)
        return key if value == f"[{key}]" else value

    def _create_bar(self, parent):
        wx = self.wx

        class GradientProgressBar(wx.Panel):
            def __init__(self, owner):
                super().__init__(owner, size=wx.Size(-1, 16))
                self._value = 0
                self.SetMinSize(wx.Size(100, 16))
                self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
                self.Bind(wx.EVT_PAINT, self._paint)

            def SetValue(self, value: int) -> None:
                self._value = max(0, min(100, int(value)))
                self.Refresh(False)

            def _paint(self, _event) -> None:
                dc = wx.AutoBufferedPaintDC(self)
                dc.SetBackground(wx.Brush(self.GetBackgroundColour()))
                dc.Clear()
                width, height = self.GetClientSize()
                gc = wx.GraphicsContext.Create(dc)
                if gc is None or width <= 0 or height <= 0:
                    return
                gc.SetBrush(wx.Brush(wx.Colour(225, 228, 232)))
                gc.SetPen(wx.TRANSPARENT_PEN)
                gc.DrawRoundedRectangle(0, 0, width, height, height / 2)
                fill_width = int(width * self._value / 100)
                if fill_width <= 0:
                    return
                red = wx.Colour(220, 53, 69)
                green = wx.Colour(34, 177, 76)
                gradient = gc.CreateLinearGradientBrush(0, 0, width, 0, red, green)
                gc.SetBrush(gradient)
                gc.DrawRoundedRectangle(0, 0, fill_width, height, height / 2)

        return GradientProgressBar(parent)

    def set_stage(self, label: str, percent: int | None = None) -> None:
        def apply() -> None:
            if percent is not None:
                self.value = max(self.value, max(0, min(100, int(percent))))
            self.stage.SetLabel(label)
            self.bar.SetValue(self.value)
            if not self.history or self.history[-1] != label:
                self.history.append(label)
                del self.history[:-5]
                self.log.SetValue("\n".join(self.history))
                self.log.ShowPosition(self.log.GetLastPosition())

        try:
            self.wx.CallAfter(apply)
        except Exception:
            apply()

    def reset(self) -> None:
        self.history.clear()
        self.value = 0

    def on_ssh_message(self, message: str) -> None:
        import re

        lower = str(message).lower()
        if "retrying in" in lower:
            match = re.search(r"attempt (\d+)/(\d+)", lower)
            attempt, maximum = match.groups() if match else ("?", "?")
            self.set_stage(
                self._text("connection.progress_retry").format(
                    attempt=attempt, total=maximum
                ),
                18,
            )
        elif "connecting to" in lower:
            self.set_stage(self._text("connection.progress_network"), 24)
        elif "negotiating transport" in lower:
            self.set_stage(self._text("connection.progress_handshake"), 48)
        elif "authentication completed" in lower:
            self.set_stage(self._text("connection.progress_authenticated"), 68)
        elif "opening remote shell and sftp" in lower:
            self.set_stage(self._text("connection.progress_sftp"), 86)
        elif "connected, sftp ready" in lower:
            self.set_stage(self._text("connection.progress_ready"), 100)
        elif "using configured key" in lower:
            self.set_stage(self._text("connection.progress_authentication"), 34)
        else:
            self.set_stage(str(message))


__all__ = ["ConnectionProgressView"]

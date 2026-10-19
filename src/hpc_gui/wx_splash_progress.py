"""Custom progress gauge used by the startup splash."""

from __future__ import annotations


def create_splash_gauge(wx, parent):
    """Create the splash's DPI-safe filled progress bar."""
    class SplashGauge(wx.Panel):
        def __init__(self, owner):
            super().__init__(owner, style=wx.BORDER_NONE)
            self.SetMinSize(wx.Size(-1, 18))
            self.SetBackgroundColour(wx.Colour(229, 231, 235))
            self._range = 100
            self._value = 100
            self._fill = wx.Panel(self, style=wx.BORDER_NONE)
            self._fill.SetBackgroundColour(wx.Colour(37, 99, 235))
            self.Bind(wx.EVT_SIZE, self._on_size)
            self.Bind(wx.EVT_PAINT, self._on_paint)

        def _on_size(self, event):
            self._update_fill()
            event.Skip()

        def _on_paint(self, event):
            event.Skip()

        def _update_fill(self):
            try:
                size = self.GetClientSize()
                width = int(size.width * max(0, min(1, self._value / max(1, self._range))))
                if width <= 0:
                    self._fill.Hide()
                else:
                    self._fill.SetSize(wx.Size(width, size.height))
                    self._fill.SetPosition(wx.Point(0, 0))
                    self._fill.Show()
                self.Refresh()
            except Exception:
                pass

        def SetValue(self, value):
            self._value = max(0, min(self._range, int(value)))
            self._update_fill()

        def GetValue(self):
            return self._value

        def GetRange(self):
            return self._range

        def SetRange(self, value):
            self._range = max(1, int(value))
            self._update_fill()

        def Pulse(self):
            self.SetValue(self._range)

        def SetForegroundColour(self, colour):
            try:
                self._fill.SetBackgroundColour(colour)
            except Exception:
                pass

        def SetBackgroundColour(self, colour):
            try:
                super().SetBackgroundColour(colour)
            except Exception:
                pass

    gauge = SplashGauge(parent)
    gauge.SetValue(0)
    return gauge

"""Custom splash progress gauge component."""

def create_splash_gauge(wx, parent):
    class _SplashGauge(wx.Panel):
        def __init__(self, parent):
            super().__init__(parent, style=wx.BORDER_NONE)
            self.SetMinSize(wx.Size(-1, 18))
            self.SetBackgroundColour(wx.Colour(229, 231, 235))
            self._range = 100
            self._value = 100
            self._fill = wx.Panel(self, style=wx.BORDER_NONE)
            self._fill.SetBackgroundColour(wx.Colour(37, 99, 235))
            # Use absolute positioning for reliable fill; sizer proportion caused 0-width on some DPIs
            self.Bind(wx.EVT_SIZE, self._on_size)
            self.Bind(wx.EVT_PAINT, self._on_paint)
        def _on_size(self, evt):
            self._update_fill()
            evt.Skip()
        def _on_paint(self, evt):
            evt.Skip()
        def _update_fill(self):
            try:
                sz = self.GetClientSize()
                w = int(sz.width * max(0, min(1, self._value / max(1, self._range))))
                # Ensure at 100% we fill exactly, at 0 we hide
                if w <= 0:
                    self._fill.Hide()
                else:
                    self._fill.SetSize(wx.Size(w, sz.height))
                    self._fill.SetPosition(wx.Point(0, 0))
                    self._fill.Show()
                self.Refresh()
            except Exception:
                pass
        def SetValue(self, v):
            self._value = max(0, min(self._range, int(v)))
            self._update_fill()
        def GetValue(self):
            return self._value
        def GetRange(self):
            return self._range
        def SetRange(self, r):
            self._range = max(1, int(r))
            self._update_fill()
        def Pulse(self):
            # Keep full — no indeterminate
            self.SetValue(self._range)
        def SetForegroundColour(self, c):
            try:
                self._fill.SetBackgroundColour(c)
            except Exception:
                pass
        def SetBackgroundColour(self, c):
            try:
                super().SetBackgroundColour(c)
            except Exception:
                pass

    return _SplashGauge(parent)

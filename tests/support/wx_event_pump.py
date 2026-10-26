"""Small event-loop helpers for tests that exercise GUI-thread callbacks."""


def pump_wx_events() -> None:
    try:
        import wx

        app = wx.App.Get()
        if app is not None:
            app.ProcessPendingEvents()
            wx.YieldIfNeeded()
    except Exception:
        pass

"""Host abstraction for wx panel/frame factories."""

from __future__ import annotations


def make_host(parent, *, title, size, embedded):
    """Return (host, finish) where host is a wx.Panel when embedded else a wx.Frame."""
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc

    if embedded:
        host = wx.Panel(parent)

        def set_host_title(text):
            host._wx_host_title = text

        class _SyntheticCloseEvent:
            """Stand-in so a panel teardown can reuse the frame EVT_CLOSE handler."""

            def Skip(self):
                pass

            def Veto(self):
                pass

        def bind_host_close(cb):
            host._wx_host_close = lambda event=None: cb(event if event is not None else _SyntheticCloseEvent())

        host._wx_host_title = title
        host._wx_host_close = None
        host.set_host_title = set_host_title
        host.bind_host_close = bind_host_close

        def finish():
            # A wx.Frame auto-expands its single child; a wx.Panel does not, so an
            # embedded host whose builder sized only an inner panel would render
            # collapsed. Give it an expanding sizer unless the builder set one.
            if host.GetSizer() is None:
                children = host.GetChildren()
                if children:
                    sizer = wx.BoxSizer(wx.VERTICAL)
                    for child in children:
                        sizer.Add(child, 1, wx.EXPAND)
                    host.SetSizer(sizer)
            host.Layout()

        return host, finish
    else:
        host = wx.Frame(parent, title=title, size=size)

        def set_host_title(text):
            host.SetTitle(text)

        def bind_host_close(cb):
            host.Bind(wx.EVT_CLOSE, cb)

        host.set_host_title = set_host_title
        host.bind_host_close = bind_host_close
        host._wx_host_title = title
        host._wx_host_close = None

        def finish():
            host.Show()

        return host, finish


__all__ = ["make_host"]

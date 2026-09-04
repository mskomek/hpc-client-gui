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

        def bind_host_close(cb):
            host._wx_host_close = cb

        host._wx_host_title = title
        host._wx_host_close = None
        host.set_host_title = set_host_title
        host.bind_host_close = bind_host_close

        def finish():
            pass

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

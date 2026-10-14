"""Small layout helpers for the embedded wx shell."""

from __future__ import annotations


def center_splitter_on_first_layout(wx, splitter) -> None:
    """Start a two-pane workspace at 50/50 once its real width is available."""
    if splitter is None:
        return
    state = {"centered": False}

    def center(event=None):
        if state["centered"]:
            if event is not None:
                event.Skip()
            return
        try:
            width = int(splitter.GetClientSize().width)
            if width > 0 and splitter.IsSplit():
                minimum = max(0, int(splitter.GetMinimumPaneSize()))
                position = width // 2
                if width >= minimum * 2:
                    position = max(minimum, min(width - minimum, position))
                splitter.SetSashPosition(position)
                state["centered"] = True
                splitter.Unbind(wx.EVT_SIZE, handler=center)
        except Exception:
            pass
        if event is not None:
            event.Skip()

    splitter.Bind(wx.EVT_SIZE, center)
    wx.CallAfter(center)

"""Small layout helpers for the embedded wx shell."""

from __future__ import annotations


def center_splitter_on_first_layout(wx, splitter) -> None:
    """Keep a two-pane workspace centered through initial layout and resize."""
    if splitter is None:
        return

    def center(event=None):
        try:
            width = int(splitter.GetClientSize().width)
            if width > 0 and splitter.IsSplit():
                minimum = max(0, int(splitter.GetMinimumPaneSize()))
                position = width // 2
                if width >= minimum * 2:
                    position = max(minimum, min(width - minimum, position))
                if splitter.GetSashPosition() != position:
                    splitter.SetSashPosition(position)
        except Exception:
            pass
        if event is not None:
            event.Skip()

    splitter.Bind(wx.EVT_SIZE, center)
    wx.CallAfter(center)

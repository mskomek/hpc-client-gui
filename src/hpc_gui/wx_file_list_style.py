"""Shared native styling helpers for wx file-list rows."""


def alternate_row_colour(wx):
    """Return a subtle stripe colour derived from the active system palette."""
    background = wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW)
    alternate = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE)
    if alternate == background:
        delta = -10 if sum(background.Get()[:3]) > 382 else 10
        alternate = wx.Colour(
            *(max(0, min(255, channel + delta)) for channel in background.Get()[:3])
        )
    return alternate

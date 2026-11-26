"""Shared product icon for wx windows, including packaged runs."""
from __future__ import annotations

from pathlib import Path


def product_icon_path() -> Path:
    return Path(__file__).resolve().parent / "assets" / "branding" / "hpc-client-gui.png"


def apply_product_icon(window) -> bool:
    import wx

    image = wx.Image(str(product_icon_path()), wx.BITMAP_TYPE_PNG)
    if not image.IsOk():
        return False
    bundle = wx.IconBundle()
    sizes = {(size, size) for size in (16, 24, 32, 48, 64)}
    for x, y in ((wx.SYS_ICON_X, wx.SYS_ICON_Y), (wx.SYS_SMALLICON_X, wx.SYS_SMALLICON_Y)):
        width, height = wx.SystemSettings.GetMetric(x), wx.SystemSettings.GetMetric(y)
        if width > 0 and height > 0:
            sizes.add((width, height))
    for width, height in sorted(sizes):
        bitmap = wx.Bitmap(image.Scale(width, height, wx.IMAGE_QUALITY_HIGH))
        icon = wx.Icon()
        icon.CopyFromBitmap(bitmap)
        if icon.IsOk():
            bundle.AddIcon(icon)
    if bundle.GetIconCount() == 0:
        return False
    window.SetIcons(bundle)
    return True

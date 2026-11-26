"""Shared product icon for wx windows, including packaged runs."""
from __future__ import annotations

from pathlib import Path


def product_icon_path() -> Path:
    return Path(__file__).resolve().parent / "assets" / "branding" / "hpc-client-gui.png"


def apply_product_icon(window) -> bool:
    import wx

    bitmap = wx.Bitmap(str(product_icon_path()), wx.BITMAP_TYPE_PNG)
    if not bitmap.IsOk():
        return False
    icon = wx.Icon()
    icon.CopyFromBitmap(bitmap)
    if not icon.IsOk():
        return False
    window.SetIcon(icon)
    return True

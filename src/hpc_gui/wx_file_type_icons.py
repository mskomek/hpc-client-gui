"""Small native wx image-list icons shared by local and remote browsers."""

from __future__ import annotations

from hpc_gui.services.directory_file_types import (
    DIRECTORY_FILE_ICON_SPECS,
    directory_file_icon_key,
)

_ICON_INDEX = {
    spec: index for index, spec in enumerate(DIRECTORY_FILE_ICON_SPECS)
}


def file_type_icon_index(name: str, is_directory: bool) -> int:
    """Return the image-list index for a file or folder entry."""
    return _ICON_INDEX[directory_file_icon_key(name, is_directory)]


def _draw_bitmap(wx, label: str, color: str):
    bitmap = wx.Bitmap(16, 16, 24)
    dc = wx.MemoryDC(bitmap)
    mask_color = wx.Colour(255, 0, 255)
    accent = wx.Colour(color)
    dc.SetBackground(wx.Brush(mask_color))
    dc.Clear()
    dc.SetPen(wx.Pen(wx.Colour(90, 103, 120), 1))

    if label == "folder":
        dc.SetBrush(wx.Brush(accent))
        dc.DrawPolygon((wx.Point(1, 4), wx.Point(6, 4), wx.Point(8, 6),
                        wx.Point(15, 6), wx.Point(14, 14), wx.Point(1, 14)))
        dc.SetPen(wx.Pen(wx.Colour(255, 220, 121), 1))
        dc.DrawLine(3, 8, 12, 8)
    else:
        dc.SetBrush(wx.Brush(wx.Colour(255, 255, 255)))
        dc.DrawPolygon((wx.Point(3, 1), wx.Point(10, 1), wx.Point(14, 5),
                        wx.Point(14, 14), wx.Point(3, 14)))
        dc.SetPen(wx.Pen(accent, 2))
        dc.DrawLine(5, 9, 12, 9)
        dc.DrawLine(5, 12, 10, 12)

    dc.SelectObject(wx.NullBitmap)
    return bitmap, mask_color


def install_file_type_icons(wx, listing):
    """Attach and return a masked image list for a wx report ListCtrl."""
    images = wx.ImageList(16, 16, True, len(DIRECTORY_FILE_ICON_SPECS))
    for label, color in DIRECTORY_FILE_ICON_SPECS:
        bitmap, mask_color = _draw_bitmap(wx, label, color)
        images.Add(bitmap, mask_color)
    listing.SetImageList(images, wx.IMAGE_LIST_SMALL)
    return images

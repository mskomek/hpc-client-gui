"""Platform-aware native coordinates for synthetic wx context-menu events."""

from __future__ import annotations


def prepare_visible_frame(app, frame, wx_module):
    """Map and lay out a test frame before synthesizing pointer coordinates."""
    frame.SetSize(wx_module.Size(1100, 760))
    frame.Show()
    frame.Layout()
    frame.SendSizeEvent()
    app.ProcessPendingEvents()
    wx_module.YieldIfNeeded()
    frame.Layout()
    app.ProcessPendingEvents()
    return frame


def context_menu_screen_point(listing, row: int, wx_module):
    """Return a screen point that the active wx port hit-tests as ``row``.

    GTK includes the report-list header offset in GetItemRect while HitTest
    uses client coordinates relative to the body. Search around the corrected
    row center so tests exercise the same row a native pointer event would.
    """
    if row < 0 or row >= listing.GetItemCount():
        raise AssertionError(f"row {row} is outside the listing")
    rect = listing.GetItemRect(row)
    item_zero_y = listing.GetItemRect(0).GetY()
    size = listing.GetClientSize()
    center_y = rect.GetY() + max(1, rect.GetHeight() // 2) - item_zero_y
    center_y = min(max(0, center_y), max(0, size.height - 1))
    x = min(5, max(0, size.width - 1))

    for distance in range(max(1, size.height)):
        for y in (center_y - distance, center_y + distance):
            if y < 0 or y >= size.height:
                continue
            hit = listing.HitTest(wx_module.Point(x, y))
            hit_row = hit[0] if isinstance(hit, tuple) else hit
            if hit_row == row:
                return listing.ClientToScreen(wx_module.Point(x, y))
    raise AssertionError(f"row {row} has no hit-testable context-menu point")


def notebook_context_screen_point(notebook, page: int, wx_module):
    """Return a screen point inside a notebook tab for context-menu tests.

    GTK can report the new page immediately while its native tab geometry is
    still stale. Give the parent frame a short layout/event cycle before
    searching for a point that the real notebook hit test recognizes.
    """
    if page < 0 or page >= notebook.GetPageCount():
        raise AssertionError(f"page {page} is outside the notebook")
    frame = notebook.GetTopLevelParent()
    app = wx_module.GetApp()
    for _ in range(20):
        frame.Layout()
        frame.SendSizeEvent()
        app.ProcessPendingEvents()
        wx_module.YieldIfNeeded()
        size = notebook.GetClientSize()
        for y in range(min(size.height, 80)):
            for x in range(size.width):
                hit = notebook.HitTest(wx_module.Point(x, y))
                hit_page = hit[0] if isinstance(hit, tuple) else hit
                if hit_page == page:
                    point = wx_module.Point(x, y)
                    return notebook.ClientToScreen(point)
        wx_module.MilliSleep(10)
    raise AssertionError(f"page {page} has no hit-testable tab point")

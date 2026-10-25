"""GTK notebook sizing compatibility for embedded shell pages."""

from __future__ import annotations


_GTK_PAGE_INSET_FALLBACK = (2, 39)


def bind_notebook_page_resize(wx, frame, notebook) -> None:
    """Keep GTK notebook pages sized when native resize events miss them.

    wxGTK can resize the notebook while leaving its page windows at their
    original allocation. The fallback derives the tab/border inset from the
    initial allocation when it is plausible, then updates every page after
    frame, notebook, and tab-selection events. Other wx ports keep their
    native page sizing behavior.
    """
    if getattr(wx, "Platform", None) != "__WXGTK__":
        return

    state = {"insets": None, "scheduled": False}

    def _measure_insets(client, page):
        page_size = page.GetSize()
        width = client.width - page_size.width
        height = client.height - page_size.height
        if 0 <= width <= 16 and 0 <= height <= 64:
            return width, height
        return _GTK_PAGE_INSET_FALLBACK

    def _resize_pages() -> None:
        state["scheduled"] = False
        try:
            if frame.IsBeingDeleted() or notebook.IsBeingDeleted():
                return
            client = notebook.GetClientSize()
            if client.width <= 0 or client.height <= 0:
                return
            if state["insets"] is None:
                selection = notebook.GetSelection()
                page_index = selection if selection >= 0 else 0
                if notebook.GetPageCount() <= page_index:
                    return
                state["insets"] = _measure_insets(
                    client, notebook.GetPage(page_index)
                )
            inset_width, inset_height = state["insets"]
            page_size = wx.Size(
                max(1, client.width - inset_width),
                max(1, client.height - inset_height),
            )
            for index in range(notebook.GetPageCount()):
                page = notebook.GetPage(index)
                if page is None or page.GetSize() == page_size:
                    continue
                page.SetSize(page_size)
                page.Layout()
        except Exception:
            # The notebook may already be shutting down when a queued resize
            # runs. Its lifetime is owned by the shell frame.
            return

    def _schedule_resize(event=None) -> None:
        if event is not None:
            event.Skip()
        if state["scheduled"]:
            return
        try:
            if frame.IsBeingDeleted() or wx.GetApp() is None:
                return
        except Exception:
            return
        state["scheduled"] = True
        try:
            wx.CallAfter(_resize_pages)
        except Exception:
            state["scheduled"] = False

    frame.Bind(wx.EVT_SIZE, _schedule_resize)
    notebook.Bind(wx.EVT_SIZE, _schedule_resize)
    notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, _schedule_resize)

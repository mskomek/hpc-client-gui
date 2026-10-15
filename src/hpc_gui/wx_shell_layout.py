"""Small layout helpers for the embedded wx shell."""

from __future__ import annotations


def center_splitter_on_first_layout(wx, splitter) -> None:
    """Keep a two-pane workspace centered through initial layout and resize."""
    if splitter is None:
        return
    state = {"alive": True}

    def stop_centering(event=None):
        state["alive"] = False
        if event is not None:
            event.Skip()

    def center(event=None):
        if not state["alive"]:
            if event is not None:
                event.Skip()
            return
        try:
            is_being_deleted = getattr(splitter, "IsBeingDeleted", None)
            if callable(is_being_deleted) and is_being_deleted():
                state["alive"] = False
                return
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

    destroy_event = getattr(wx, "EVT_WINDOW_DESTROY", None)
    if destroy_event is not None:
        splitter.Bind(destroy_event, stop_centering)
    get_owner = getattr(splitter, "GetTopLevelParent", None)
    owner = get_owner() if callable(get_owner) else None
    close_event = getattr(wx, "EVT_CLOSE", None)
    if owner is not None and owner is not splitter and close_event is not None:
        owner.Bind(close_event, stop_centering)
    splitter.Bind(wx.EVT_SIZE, center)
    wx.CallAfter(center)

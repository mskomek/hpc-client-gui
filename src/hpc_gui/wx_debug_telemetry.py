"""Scoped source-only wx interaction telemetry; no global native event filter."""
from __future__ import annotations

import weakref

from hpc_gui.core.debug_telemetry import TelemetryRecorder, is_source_run


def install_wx_debug_telemetry(frame, notebook, *, recorder=None):
    """Observe the main shell without reading labels, inputs, or terminal content."""
    if not is_source_run():
        return None
    import wx

    recorder = recorder or TelemetryRecorder()
    state = {"index": notebook.GetSelection(), "since": recorder.clock(), "generation": 0}
    notebook_ref = weakref.ref(notebook)
    safe_keys = {
        wx.WXK_DELETE, wx.WXK_BACK, wx.WXK_ESCAPE, wx.WXK_TAB,
        wx.WXK_LEFT, wx.WXK_RIGHT, wx.WXK_UP, wx.WXK_DOWN,
        wx.WXK_HOME, wx.WXK_END, wx.WXK_PAGEUP, wx.WXK_PAGEDOWN,
        *(getattr(wx, f"WXK_F{i}") for i in range(1, 13)),
    }

    def on_button(event):
        try:
            target = event.GetEventObject()
            recorder.action(type(target).__name__)
        finally:
            event.Skip()

    def on_key(event):
        try:
            focused = wx.Window.FindFocus()
            # Text entry and printable keys are excluded even in a source run.
            if (focused is not None and not isinstance(focused, wx.TextEntry)
                    and event.GetKeyCode() in safe_keys):
                recorder.key(type(focused).__name__, event.GetKeyCode(), event.GetModifiers())
        finally:
            event.Skip()

    def on_tab(event):
        try:
            book = notebook_ref()
            if book is None or event.GetEventObject() is not book:
                return
            index = event.GetSelection()
            if index == state["index"] or index < 0:
                return
            since = recorder.tab_changed("main", state["index"], index, state["since"])
            state.update(index=index, since=since, generation=state["generation"] + 1)
            generation = state["generation"]

            def ready():
                current = notebook_ref()
                try:
                    if (current is not None and not current.IsBeingDeleted()
                            and state["generation"] == generation
                            and current.GetSelection() == index):
                        recorder.tab_ready("main", index, since)
                except RuntimeError:
                    # A queued event may run after native window destruction.
                    pass

            wx.CallAfter(ready)
        finally:
            event.Skip()

    frame.Bind(wx.EVT_BUTTON, on_button)
    frame.Bind(wx.EVT_CHAR_HOOK, on_key)
    notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, on_tab)
    return recorder

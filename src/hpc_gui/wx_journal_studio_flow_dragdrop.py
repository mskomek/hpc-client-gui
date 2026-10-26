"""Handle internal pointer drags between the command catalog and Visual Flow."""

from __future__ import annotations

from hpc_gui.core.i18n import t


def bind_flow_dragdrop(editor) -> None:
    """Bind internal drags without entering wx's native OLE drag loop."""
    wx = editor.wx
    sources = {"library": editor.library, "structure": editor.structure}
    states = {kind: {} for kind in sources}
    handlers = {}
    timer = wx.Timer(editor.page)
    editor._flow_drag_states = states
    editor._flow_drag_handlers = handlers
    editor._flow_drag_timer = timer

    def stop_if_idle():
        if not any(state.get("origin") is not None for state in states.values()):
            timer.Stop()

    def reset_drag(kind, *, refresh=True):
        state = states[kind]
        window = sources[kind]
        cursor = state.get("cursor")
        if cursor is not None:
            window.SetCursor(cursor)
        state.clear()
        stop_if_idle()
        if refresh:
            editor._refresh_status()

    def make_payload(kind, index):
        if kind == "library" and 0 <= index < len(editor._library_entries):
            return "ansys-journal-command:" + editor._library_entries[index]["command_path"]
        if kind == "structure" and 0 <= index < len(editor._parsed.blocks):
            return f"ansys-journal-block:{index}"
        return None

    def finish_drag(kind, screen_point):
        state = states[kind]
        payload = state.get("payload")
        reset_drag(kind)
        target_rect = editor.structure.GetScreenRect()
        if payload and target_rect.Contains(screen_point):
            point = editor.structure.ScreenToClient(screen_point)
            editor._drop_flow_item(point.x, point.y, payload)
            editor._refresh_status()

    def update_drag(kind, screen_point, left_down):
        state = states[kind]
        origin = state.get("origin")
        if origin is None:
            return
        if not left_down:
            finish_drag(kind, screen_point)
            return
        if state.get("dragging"):
            return
        if max(abs(screen_point.x - origin.x), abs(screen_point.y - origin.y)) < 5:
            return
        payload = make_payload(kind, state.get("index", -1))
        if payload is None:
            reset_drag(kind)
            return
        window = sources[kind]
        state["payload"] = payload
        state["dragging"] = True
        state["cursor"] = window.GetCursor()
        window.SetCursor(wx.Cursor(wx.CURSOR_HAND))
        editor.status.SetLabel(t("journal_studio.drag_drop_hint"))

    def begin_drag(kind, event):
        window = sources[kind]
        state = states[kind]
        state.clear()
        index = window.HitTest(event.GetPosition())
        if index == wx.NOT_FOUND:
            index = window.GetSelection()
        if index >= 0:
            window.SetSelection(index)
        state["origin"] = wx.GetMousePosition()
        state["index"] = index
        timer.Start(30)
        event.Skip()

    def bind_source(kind, window):
        def on_left_down(event):
            begin_drag(kind, event)

        def on_motion(event):
            update_drag(kind, wx.GetMousePosition(), event.LeftIsDown())
            event.Skip()

        def on_left_up(event):
            update_drag(kind, wx.GetMousePosition(), False)
            event.Skip()

        handlers[kind] = {
            "left_down": on_left_down,
            "motion": on_motion,
            "left_up": on_left_up,
        }
        window.Bind(wx.EVT_LEFT_DOWN, on_left_down)
        window.Bind(wx.EVT_LEFT_UP, on_left_up)
        window.Bind(wx.EVT_MOTION, on_motion)

    def on_timer(event):
        screen_point = wx.GetMousePosition()
        left_down = wx.GetMouseState().LeftIsDown()
        for kind, state in states.items():
            if state.get("origin") is not None:
                update_drag(kind, screen_point, left_down)
        stop_if_idle()

    bind_source("library", editor.library)
    bind_source("structure", editor.structure)
    editor.page.Bind(wx.EVT_TIMER, on_timer, timer)
    handlers["timer"] = on_timer

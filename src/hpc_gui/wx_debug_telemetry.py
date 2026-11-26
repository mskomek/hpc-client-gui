"""Scoped source-only wx interaction telemetry; no global native event filter."""
from __future__ import annotations

import weakref

from hpc_gui.core.debug_telemetry import TelemetryRecorder, is_source_run


def handle_navigation_key(wx, recorder, event, *, focused=None) -> None:
    """Record only structural navigation keys; never text or printable input."""
    safe_keys = {
        wx.WXK_DELETE, wx.WXK_BACK, wx.WXK_ESCAPE, wx.WXK_TAB,
        wx.WXK_LEFT, wx.WXK_RIGHT, wx.WXK_UP, wx.WXK_DOWN,
        wx.WXK_HOME, wx.WXK_END, wx.WXK_PAGEUP, wx.WXK_PAGEDOWN,
        *(getattr(wx, f"WXK_F{i}") for i in range(1, 13)),
    }

    navigation_controls = (wx.Button, wx.ListCtrl, wx.TreeCtrl, wx.Notebook, wx.CheckBox, wx.RadioButton)

    try:
        if focused is None:
            focused = wx.Window.FindFocus()
        if (focused is not None and isinstance(focused, navigation_controls)
                and event.GetKeyCode() in safe_keys):
            recorder.key(type(focused).__name__, event.GetKeyCode(), event.GetModifiers())
    except (AttributeError, RuntimeError):
        pass
    finally:
        event.Skip()


def install_wx_debug_telemetry(frame, notebook, *, recorder=None):
    """Observe the main shell without reading labels, inputs, or terminal content."""
    if not is_source_run():
        return None
    import wx

    recorder = recorder or TelemetryRecorder()
    state = {"index": notebook.GetSelection(), "since": recorder.clock(), "generation": 0}
    notebook_ref = weakref.ref(notebook)

    def on_button(event):
        try:
            target = event.GetEventObject()
            recorder.action(type(target).__name__)
        except (AttributeError, RuntimeError):
            pass
        finally:
            event.Skip()

    def on_key(event):
        handle_navigation_key(wx, recorder, event)

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
        except (AttributeError, RuntimeError):
            pass
        finally:
            event.Skip()

    frame.Bind(wx.EVT_BUTTON, on_button)
    frame.Bind(wx.EVT_CHAR_HOOK, on_key)
    notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, on_tab)
    return recorder


def observe_wx_window(window, *, recorder=None):
    """Observe a specific owned top-level, never a global native event filter."""
    if not is_source_run():
        return None
    import wx

    existing = getattr(window, "_wx_window_telemetry", None)
    if existing is not None:
        return existing
    recorder = recorder or TelemetryRecorder()
    kind = type(window).__name__
    state = {"since": None, "generation": 0}
    ref = weakref.ref(window)

    def hidden():
        since = state["since"]
        state["since"] = None
        state["generation"] += 1
        if since is not None:
            recorder.window_hidden(kind, since)

    def on_show(event):
        try:
            if event.GetEventObject() is not window:
                return
            if not event.IsShown():
                hidden()
                return
            if state["since"] is not None:
                return
            since = recorder.clock()
            state["since"] = since
            state["generation"] += 1
            generation = state["generation"]
            recorder.window_shown(kind)

            def ready():
                current = ref()
                try:
                    if (current is not None and not current.IsBeingDeleted()
                            and current.IsShown() and state["generation"] == generation):
                        recorder.window_ready(kind, since)
                except RuntimeError:
                    pass

            wx.CallAfter(ready)
        except (AttributeError, RuntimeError):
            pass
        finally:
            event.Skip()

    def on_destroy(event):
        try:
            if event.GetWindow() is window:
                hidden()
        except (AttributeError, RuntimeError):
            pass
        finally:
            event.Skip()

    window.Bind(wx.EVT_SHOW, on_show)
    window.Bind(wx.EVT_WINDOW_DESTROY, on_destroy)
    window._wx_window_telemetry = recorder
    return recorder


def install_optional_window_telemetry(window) -> None:
    try:
        observe_wx_window(window)
    except Exception:
        # Diagnostics must not prevent creating the real window.
        pass

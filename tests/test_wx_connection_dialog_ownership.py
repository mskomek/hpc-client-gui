from __future__ import annotations

import pytest

wx = pytest.importorskip("wx")

from hpc_gui.wx_connection_dialog import WxConnectionDialog


def _nested_windows(sizer):
    for item in sizer.GetChildren():
        child_sizer = item.GetSizer()
        if child_sizer is not None:
            yield from _nested_windows(child_sizer)
        child_window = item.GetWindow()
        if child_window is not None:
            yield child_window


@pytest.mark.wx
@pytest.mark.integration
def test_static_box_children_are_owned_by_their_static_box():
    app = wx.GetApp() or wx.App(False)
    frame = wx.Frame(None)
    dialog = WxConnectionDialog(frame, mode="add")
    try:
        stack = [dialog.dlg.GetSizer()]
        static_box_sizers = []
        while stack:
            sizer = stack.pop()
            for item in sizer.GetChildren():
                nested = item.GetSizer()
                if nested is not None:
                    stack.append(nested)
                    if isinstance(nested, wx.StaticBoxSizer):
                        static_box_sizers.append(nested)
                window = item.GetWindow()
                if window is not None and window.GetSizer() is not None:
                    stack.append(window.GetSizer())

        assert static_box_sizers
        mismatches = []
        for section in static_box_sizers:
            box = section.GetStaticBox()
            for child in _nested_windows(section):
                if child.GetParent() is not box:
                    mismatches.append((child.GetClassName(), box.GetLabel(), child.GetParent().GetClassName()))
        assert mismatches == []
    finally:
        dialog.Destroy()
        frame.Destroy()
        app.Yield()


@pytest.mark.wx
@pytest.mark.integration
def test_connection_dialog_destroy_is_idempotent():
    app = wx.GetApp() or wx.App(False)
    frame = wx.Frame(None)
    dialog = WxConnectionDialog(frame, mode="add")
    dialog.Destroy()
    dialog.Destroy()
    frame.Destroy()
    app.Yield()

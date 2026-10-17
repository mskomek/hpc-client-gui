from __future__ import annotations

import threading
import time
from pathlib import Path
from types import SimpleNamespace
import pytest
wx = pytest.importorskip("wx")
from hpc_gui.core.i18n import current_language, set_language, t
from hpc_gui.wx_shell import create_shell_frame
def _yield(n: int = 1) -> None:
    for _ in range(n):
        try:
            wx.SafeYield()
        except Exception:
            pass
        wx.MilliSleep(1)
def _click(btn) -> None:
    evt = wx.CommandEvent(wx.wxEVT_BUTTON, btn.GetId())
    btn.GetEventHandler().ProcessEvent(evt)
def _toggle(cb, v: bool) -> None:
    cb.SetValue(v)
    evt = wx.CommandEvent(wx.wxEVT_CHECKBOX, cb.GetId())
    evt.SetInt(1 if v else 0)
    cb.GetEventHandler().ProcessEvent(evt)
def _menu(frame, mid: int) -> None:
    evt = wx.CommandEvent(wx.wxEVT_MENU, mid)
    frame.GetEventHandler().ProcessEvent(evt)
def _cleanup_wx_test(app, existing_windows, original_language) -> None:
    set_language(original_language)
    created_windows = [window for window in wx.GetTopLevelWindows() if window not in existing_windows]
    for window in created_windows:
        try:
            window.Close()
        except Exception:
            pass
    for _ in range(3):
        app.ProcessPendingEvents()
        _yield(1)
    for window in created_windows:
        try:
            if not window.IsBeingDeleted():
                window.Destroy()
        except Exception:
            pass
    for _ in range(2):
        app.ProcessPendingEvents()
        _yield(1)
    remaining = [window for window in wx.GetTopLevelWindows() if window not in existing_windows]
    assert not remaining, "wx top-level windows survived test cleanup"
class Probe:
    def __init__(self) -> None:
        self.count = 0
        self._marks: list[dict] = []

    def watch(self, ctrl) -> None:
        mark = {"d": False}
        for name in ("DeleteAllItems", "InsertItem", "SetItem", "SetValue", "Enable"):
            orig = getattr(ctrl, name, None)
            if not callable(orig):
                continue

            def wrap(o, m):
                def fn(*a, **k):
                    if m["d"]:
                        self.count += 1
                        return None
                    return o(*a, **k)

                return fn

            setattr(ctrl, name, wrap(orig, mark))
        self._marks.append(mark)

    def destroy(self) -> None:
        for m in self._marks:
            m["d"] = True

__all__ = [
    'threading',
    'time',
    'Path',
    'SimpleNamespace',
    'pytest',
    'wx',
    'current_language',
    'set_language',
    't',
    'create_shell_frame',
    '_yield',
    '_click',
    '_toggle',
    '_menu',
    '_cleanup_wx_test',
    'Probe',
]

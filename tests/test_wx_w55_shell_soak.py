"""W55 run-phase regression tests (shell navigation + a11y + soak).

Purpose IDs:
- DEF-W55-A (REQ HPC-W10-GJ2-030): shell status-bar connection indicator.
- DEF-W55-B (REQ HPC-W10-GJ2-029/038): shell keyboard accelerators for tabs + Help.
Taxonomy: GUI event/integration (real wx runtime).
"""
import pytest

wx = pytest.importorskip("wx")


def _make_frame():
    from hpc_gui.wx_shell import create_shell_frame
    from hpc_gui.wx_lifecycle import WxLifecycleController

    app = wx.App.Get() or wx.App(False)
    lifecycle = WxLifecycleController()
    session_state = {"session": None, "generation": 0}
    frame, _lifecycle, _state = create_shell_frame(
        app, lifecycle=lifecycle, session_state=session_state
    )
    return app, frame, lifecycle, session_state


def _close_frame(frame):
    try:
        frame.Close()
    except Exception:
        pass
    for _ in range(3):
        try:
            wx.Yield()
        except Exception:
            break
    try:
        if not frame.IsBeingDeleted():
            frame.Destroy()
    except Exception:
        pass
    for _ in range(3):
        try:
            wx.Yield()
        except Exception:
            break


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
def test_w55_status_bar_reflects_connection_state():
    """DEF-W55-A: frame status bar must show connected/disconnected truth."""
    from hpc_gui.wx_shell import _connection_callbacks

    app, frame, lifecycle, session_state = _make_frame()
    frame.Show()
    wx.Yield()
    try:
        cbs = _connection_callbacks(session_state, frame, lifecycle)
        session = {"connected": True, "profile": {"name": "w55probe"}}
        cbs["on_connected"](session)
        wx.Yield()
        connected_text = frame.GetStatusBar().GetStatusText()
        assert "w55probe" in connected_text or "onnect" in connected_text, (
            f"status bar must reflect connected session, got: {connected_text!r}"
        )
        cbs["on_disconnected"](session)
        wx.Yield()
        idle_text = frame.GetStatusBar().GetStatusText()
        assert "w55probe" not in idle_text, (
            f"status bar must drop stale profile after disconnect, got: {idle_text!r}"
        )
    finally:
        _close_frame(frame)


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
def test_w55_shell_tab_and_help_accelerators():
    """DEF-W55-B: Ctrl+1..7 tab selection and F1 help must be accelerators."""
    app, frame, lifecycle, session_state = _make_frame()
    frame.Show()
    wx.Yield()
    try:
        from hpc_gui import wx_shell as _wx_shell_mod

        table = frame.GetAcceleratorTable()
        assert table is not None and table.IsOk(), "shell frame must carry an AcceleratorTable"
        spec = list(getattr(frame, "_wx_shell_accel_spec", []))
        flags_keys = {(flags, key) for flags, key, _cmd in spec}
        assert (int(wx.ACCEL_CTRL), ord("1")) in flags_keys, "Ctrl+1 tab accelerator missing"
        assert (int(wx.ACCEL_CTRL), ord("7")) in flags_keys, "Ctrl+7 tab accelerator missing"
        assert (int(wx.ACCEL_NORMAL), int(wx.WXK_F1)) in flags_keys, "F1 help accelerator missing"
        accel_ids = dict(getattr(frame, "_wx_shell_accel_ids", {}))
        tab_cmds = sorted(cmd for cmd, idx in accel_ids.items() if idx == 2)
        assert tab_cmds, "Ctrl+3 tab accelerator missing"
        help_cmds = [cmd for cmd, idx in accel_ids.items() if idx == "help"]
        assert help_cmds, "F1 help accelerator missing"
        # Functional proof: Ctrl+3-equivalent command selects the 3rd notebook page.
        notebook = frame._wx_shell_controls["notebook"]
        notebook.SetSelection(0)
        wx.Yield()
        evt = wx.CommandEvent(wx.wxEVT_MENU, tab_cmds[0])
        frame.GetEventHandler().ProcessEvent(evt)
        wx.Yield()
        assert notebook.GetSelection() == 2, "Ctrl+3 accelerator must select tab index 2"
        # Functional proof: F1-equivalent command routes to Help via _dispatch.
        seen = []
        real_dispatch = _wx_shell_mod._dispatch
        _wx_shell_mod._dispatch = lambda *a, **k: seen.append(a[0] if a else None)
        try:
            frame.GetEventHandler().ProcessEvent(wx.CommandEvent(wx.wxEVT_MENU, help_cmds[0]))
            wx.Yield()
        finally:
            _wx_shell_mod._dispatch = real_dispatch
        assert seen == ["APP-HELP"], f"F1 accelerator must dispatch APP-HELP, got {seen!r}"
    finally:
        _close_frame(frame)

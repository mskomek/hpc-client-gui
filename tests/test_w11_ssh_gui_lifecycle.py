"""W11 GUI connection status lifecycle regressions."""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / 'src') not in sys.path:
    sys.path.insert(0, str(ROOT / 'src'))

# GUI proof: real wx.App + Frame, real event dispatch, observable labels
# ---------------------------------------------------------------------------

def _pump_until(label_fn, expected, timeout_s=20.0):
    """Pump the real wx loop until the observable label reaches ``expected``."""
    wx = pytest.importorskip("wx")
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            wx.Yield()
        except Exception:
            pass
        try:
            if label_fn() == expected:
                return True
        except Exception:
            pass
        time.sleep(0.05)
    try:
        return label_fn() == expected
    except Exception:
        return False


def _drive_select_and_connect(ctrls):
    """Drive the real listbox + button event path (no direct handler calls)."""
    wx = pytest.importorskip("wx")
    choices = ctrls["choices"]
    connect_btn = ctrls["connect"]
    choices.SetSelection(0)
    select_evt = wx.CommandEvent(wx.wxEVT_LISTBOX, choices.GetId())
    select_evt.SetEventObject(choices)
    wx.PostEvent(choices, select_evt)
    assert _pump_until(lambda: choices.GetStringSelection() == "lab",  True, timeout_s=5.0)
    click_evt = wx.CommandEvent(wx.wxEVT_BUTTON, connect_btn.GetId())
    click_evt.SetEventObject(connect_btn)
    wx.PostEvent(connect_btn, click_evt)


@pytest.mark.wx
@pytest.mark.gui
@pytest.mark.semantic
def test_wx_panel_reports_failed_connect_as_failed(monkeypatch):
    """GUI-001 (HPC-W03-SSH-001): a refused connect never shows "Connected".

    Real ``wx.App`` + ``Frame`` + ``build_connection_panel``; selection and
    Connect travel through real posted ``wx`` command events and the worker
    thread; the observable status label is the verdict.
    """
    wx = pytest.importorskip("wx")
    from hpc_gui import wx_connection as wx_conn
    from hpc_gui.core.i18n import current_language, load_language, t

    previous_language = current_language()
    load_language("en")
    profiles = [{"name": "lab", "host": "127.0.0.1", "username": "u"}]
    monkeypatch.setattr(wx_conn, "load_profiles", lambda: [dict(p) for p in profiles])
    monkeypatch.setattr(
        "hpc_gui.services.connection_profile_service.load_profile_by_name",
        lambda name: None,
    )

    def _refused(_profile):
        raise RuntimeError("connection refused (w11 lab)")

    app = wx.App.Get() or wx.App(False)
    assert app is wx.GetApp()
    frame = wx.Frame(None, title="w11-lab-failed")
    try:
        host = wx_conn.build_connection_panel(frame, profiles=profiles, connect=_refused)
        ctrls = host._wx_connection_controls
        status = ctrls["status"]
        _drive_select_and_connect(ctrls)
        assert _pump_until(status.GetLabel, t("connection.status_failed"))
        assert status.GetLabel() != t("login.status_connected")
    finally:
        frame.Destroy()
        load_language(previous_language)


@pytest.mark.wx
@pytest.mark.gui
@pytest.mark.semantic
def test_wx_panel_transport_failure_repaints_status(monkeypatch):
    """GUI-002 (HPC-W03-SSH-001): leaving CONNECTED repaints the indicator.

    After a successful connect the panel shows "Connected"; a subsequent
    controller failure (the path ``disconnect_cb`` drives on transport
    death, see DEF-W11-001) must repaint the same label to the failed
    state instead of masquerading the dead session as live.
    """
    wx = pytest.importorskip("wx")
    from hpc_gui import wx_connection as wx_conn
    from hpc_gui.core.i18n import current_language, load_language, t

    previous_language = current_language()
    load_language("en")
    profiles = [{"name": "lab", "host": "127.0.0.1", "username": "u"}]
    monkeypatch.setattr(wx_conn, "load_profiles", lambda: [dict(p) for p in profiles])
    monkeypatch.setattr(
        "hpc_gui.services.connection_profile_service.load_profile_by_name",
        lambda name: None,
    )

    def _ok(_profile):
        return {"connected": True, "profile_name": "lab"}

    app = wx.App.Get() or wx.App(False)
    assert app is wx.GetApp()
    frame = wx.Frame(None, title="w11-lab-repaint")
    try:
        host = wx_conn.build_connection_panel(frame, profiles=profiles, connect=_ok)
        ctrls = host._wx_connection_controls
        model = host._wx_connection_model
        status = ctrls["status"]
        _drive_select_and_connect(ctrls)
        assert _pump_until(status.GetLabel, t("login.status_connected"))
        model.controller.fail()
        assert _pump_until(status.GetLabel, t("connection.status_failed"))
        assert status.GetLabel() != t("login.status_connected")
    finally:
        frame.Destroy()
        load_language(previous_language)

# ---------------------------------------------------------------------------

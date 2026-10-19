from __future__ import annotations

import pytest


def test_connection_progress_view_shows_stages_and_monotonic_gradient():
    wx = pytest.importorskip("wx")
    from hpc_gui.wx_connection_progress import ConnectionProgressView

    app = wx.App.Get() or wx.App(False)
    frame = wx.Frame(None, title="connection-progress-test")
    root = wx.BoxSizer(wx.VERTICAL)
    view = ConnectionProgressView(wx, frame, root)
    frame.SetSizer(root)
    frame.Show()
    view.reset()

    view.set_stage("Preparing credentials", 4)
    wx.YieldIfNeeded()
    assert view.stage.GetLabel() == "Preparing credentials"
    assert view.bar._value == 4

    view.on_ssh_message("SSH: negotiating transport and authenticating")
    wx.YieldIfNeeded()
    assert view.bar._value == 48
    assert "SSH handshake and authentication" in view.stage.GetLabel()
    assert "Preparing credentials" in view.log.GetValue()

    view.on_ssh_message("SSH: connection attempt 1/5 failed; retrying in 1 second (OSError)")
    wx.YieldIfNeeded()
    assert view.bar._value == 48
    assert "1/5" in view.stage.GetLabel()

    frame.Destroy()
    app.ProcessPendingEvents()

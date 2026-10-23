from __future__ import annotations

import time

import pytest


PLUGIN_ID = "org.hpcclient.ansysjournalstudio"


def _manager_model(root):
    from hpc_gui.plugins.state import write_installed_state
    from hpc_gui.plugins.storage import write_active_versions
    from hpc_gui.wx_plugins import WxPluginManagerModel

    write_installed_state(
        {PLUGIN_ID: {"versions": ["0.1.0", "0.1.1", "0.2.0", "bad"]}},
        root=root,
    )
    write_active_versions({PLUGIN_ID: "0.1.1"}, root=root)
    model = WxPluginManagerModel(root=root, app_version="1.5.9")
    model.set_registry(
        [
            {
                "id": PLUGIN_ID,
                "name": "ANSYS Journal Studio",
                "version": "0.1.1",
                "installed": True,
                "enabled": True,
                "compatible": True,
                "active_version": "0.1.1",
            }
        ],
        "cache",
    )
    return model


def test_model_returns_only_installed_older_rollback_versions(tmp_path):
    model = _manager_model(tmp_path)

    assert model.rollback_versions(PLUGIN_ID) == ("0.1.0",)


@pytest.mark.gui
@pytest.mark.wx
def test_wx_plugin_manager_confirms_and_runs_rollback(tmp_path, monkeypatch):
    wx = pytest.importorskip("wx")
    from hpc_gui.wx_plugins_view import build_plugins_panel

    app = wx.App.Get() or wx.App(False)
    frame = wx.Frame(None, title="plugin-rollback-test")
    model = _manager_model(tmp_path)
    calls = []
    model.rollback = lambda plugin_id, version: calls.append((plugin_id, version))

    class VersionChoice:
        def __init__(self, *_args):
            pass

        def ShowModal(self):
            return wx.ID_OK

        def GetStringSelection(self):
            return "0.1.0"

        def Destroy(self):
            pass

    answers = iter((wx.YES, wx.OK))
    monkeypatch.setattr(wx, "SingleChoiceDialog", VersionChoice)
    monkeypatch.setattr(wx, "MessageBox", lambda *_args: next(answers))
    try:
        panel = build_plugins_panel(frame, model, root=tmp_path, initial_tab="installed")
        controls = panel._wx_plugins_controls
        state = panel._wx_plugins_state
        listing = controls["listing"]
        listing.SetItemState(0, wx.LIST_STATE_SELECTED, wx.LIST_STATE_SELECTED)
        wx.YieldIfNeeded()
        rollback = controls["rollback"]
        assert rollback.IsEnabled()

        event = wx.CommandEvent(wx.EVT_BUTTON.typeId, rollback.GetId())
        rollback.GetEventHandler().ProcessEvent(event)
        deadline = time.monotonic() + 3.0
        while state["in_flight"] and time.monotonic() < deadline:
            wx.YieldIfNeeded()
            time.sleep(0.01)

        assert calls == [(PLUGIN_ID, "0.1.0")]
        assert state["in_flight"] is False
    finally:
        frame.Destroy()
        app.ProcessPendingEvents()


@pytest.mark.gui
@pytest.mark.wx
def test_wx_plugin_manager_remove_requires_confirmation(tmp_path, monkeypatch):
    wx = pytest.importorskip("wx")
    from hpc_gui.wx_plugins_view import build_plugins_panel

    app = wx.App.Get() or wx.App(False)
    frame = wx.Frame(None, title="plugin-remove-confirmation-test")
    model = _manager_model(tmp_path)
    removed = []
    model.remove = lambda plugin_id: removed.append(plugin_id)
    monkeypatch.setattr(wx, "MessageBox", lambda *_args: wx.NO)
    try:
        panel = build_plugins_panel(frame, model, root=tmp_path, initial_tab="installed")
        controls = panel._wx_plugins_controls
        listing = controls["listing"]
        listing.SetItemState(0, wx.LIST_STATE_SELECTED, wx.LIST_STATE_SELECTED)
        wx.YieldIfNeeded()

        event = wx.CommandEvent(wx.EVT_BUTTON.typeId, controls["remove"].GetId())
        controls["remove"].GetEventHandler().ProcessEvent(event)

        assert removed == []
    finally:
        frame.Destroy()
        app.ProcessPendingEvents()

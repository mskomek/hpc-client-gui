"""Native installed plugin tool button, disclosure and fail-closed resolution."""
import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.subprocess
def test_native_installed_trusted_tool_open(tmp_path):
    root = Path(__file__).resolve().parents[1]
    script = r"""
import sys
import wx
from types import SimpleNamespace as NS
from unittest.mock import patch
from hpc_gui.core.i18n import load_language, t
from hpc_gui.wx_plugins import WxPluginManagerModel
from hpc_gui.wx_plugins_view import build_plugins_panel

load_language("en")
app = wx.App(False)
app.SetExitOnFrameDelete(False)
frame = wx.Frame(None)
model = WxPluginManagerModel(root=sys.argv[1])
pid = "org.hpcclient.ansyslint"
model.set_registry([
    {"id":pid, "name":"Approved", "version":"1", "installed":True, "enabled":True, "capabilities":["linter-tool"]},
    {"id":"org.example.bad", "name":"Unapproved", "version":"1", "installed":True, "enabled":True, "capabilities":["linter-tool"]},
])
panel = build_plugins_panel(frame, model, initial_tab="installed")
frame.Show()
app.ProcessPendingEvents()
controls = panel._wx_plugins_controls
listing = controls["listing"]
button = controls["open_tool"]
note = controls["trusted_tool_note"]
assert not button.IsEnabled()
def select(i):
    listing.Select(i)
    event = wx.ListEvent(wx.wxEVT_LIST_ITEM_SELECTED, listing.GetId())
    event.SetIndex(i)
    event.SetEventObject(listing)
    listing.GetEventHandler().ProcessEvent(event)
    wx.Yield()
def click():
    event = wx.CommandEvent(wx.EVT_BUTTON.typeId, button.GetId())
    event.SetEventObject(button)
    button.GetEventHandler().ProcessEvent(event)
manifest = NS(id=pid, version="1", publisher="HPC Client GUI", plugin_api=2,
              capabilities=["linter-tool"], entrypoints={"linter_engine":"engine/ansys_lint/__init__.py"})
plugin = NS(manifest=manifest)
opened = []
with patch("hpc_gui.plugins.loader.load_installed_plugins", return_value=NS(plugins=[plugin])),      patch("hpc_gui.services.wx_plugin_menu_host.WxPluginMenuHost.open_trusted_tool",
           lambda self, plugin: opened.append(plugin) or True):
    select(0)
    assert button.IsEnabled()
    assert note.IsShown() and t("plugins.trusted_tool_disclosure_short") in note.GetLabel().replace("\n", " ")
    click()
    assert opened == [plugin]
    select(1)
    assert not button.IsEnabled()
    click()
    assert opened == [plugin]
    select(0)
    errors = []
    with patch("hpc_gui.plugins.loader.load_installed_plugins", return_value=NS(plugins=[])),          patch.object(wx, "MessageBox", lambda msg, *a: errors.append(msg)):
        click()
    assert len(errors) == 1 and opened == [plugin]
assert not any(m.split(".")[0] in {"PySide6", "PyQt5", "PyQt6", "shiboken6"} for m in sys.modules)
frame.Destroy()
app.ProcessPendingEvents()
"""
    env = dict(os.environ, HPC_GUI_CONFIG_ROOT=str(tmp_path))
    env["PYTHONPATH"] = os.pathsep.join([str(root / "src"), env.get("PYTHONPATH", "")])
    result = subprocess.run([sys.executable, "-u", "-X", "faulthandler", "-c", script, str(tmp_path)],
                            cwd=root, env=env, capture_output=True, text=True, timeout=35)
    assert result.returncode == 0, result.stdout + result.stderr

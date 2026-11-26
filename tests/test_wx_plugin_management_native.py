"""Real wx controls and storage-backed plugin manager lifecycle acceptance."""
import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.subprocess
def test_native_plugin_management_readback(tmp_path):
    root = Path(__file__).resolve().parents[1]
    script = r"""
import sys
import time
import wx
from unittest.mock import patch
from hpc_gui.core.i18n import load_language, t
from hpc_gui.plugins.state import record_installed_version
from hpc_gui.plugins.storage import read_active_versions, write_active_versions
from hpc_gui.services.plugin_request import PLUGIN_REQUEST_URL
from hpc_gui.wx_plugins import WxPluginManagerModel
from hpc_gui.wx_plugins_view import build_plugins_panel

load_language("en")
app = wx.App(False)
app.SetExitOnFrameDelete(False)
frame = wx.Frame(None)
root = sys.argv[1]
pid = "org.example.tool"
record_installed_version(pid, "1.0.0", root=root)
record_installed_version(pid, "2.0.0", root=root, activate=False)
model = WxPluginManagerModel(root=root, app_version="2.0.0")
model.build_cards_from_registry({"plugins":[
    {"id":pid,"name":"Example","version":v,"requires_app":">=1.0.0",
     "type":"cluster-profile","publisher":"Example","description":"Test"}
    for v in ("1.0.0","2.0.0")]}, "cache")
panel = build_plugins_panel(frame, model, initial_tab="installed")
frame.Show()
app.ProcessPendingEvents()
c = panel._wx_plugins_controls
listing = c["listing"]
state = panel._wx_plugins_state

def select():
    assert listing.GetItemCount() == 1
    listing.Select(0)
    event = wx.ListEvent(wx.wxEVT_LIST_ITEM_SELECTED, listing.GetId())
    event.SetIndex(0)
    event.SetEventObject(listing)
    listing.GetEventHandler().ProcessEvent(event)

def click(name):
    button = c[name]
    event = wx.CommandEvent(wx.EVT_BUTTON.typeId, button.GetId())
    event.SetEventObject(button)
    button.GetEventHandler().ProcessEvent(event)

def pump():
    deadline = time.monotonic() + 8
    while state["in_flight"] and time.monotonic() < deadline:
        wx.Yield()
        time.sleep(.01)
    assert not state["in_flight"]

def choose(v):
    c["versions"].SetStringSelection(v)
    event = wx.CommandEvent(wx.EVT_CHOICE.typeId, c["versions"].GetId())
    event.SetEventObject(c["versions"])
    c["versions"].GetEventHandler().ProcessEvent(event)

messages = []
answer = [wx.NO]
def message(text, title, style, parent):
    messages.append((text, title))
    return answer[0] if style & wx.YES_NO else wx.OK

def activate(plugin_id, version, root=None):
    write_active_versions({plugin_id:version}, root)

with patch.object(wx, "MessageBox", message):
    select()
    assert c["versions"].GetItems() == ["2.0.0","1.0.0"]
    click("details")
    assert "Example" in messages[-1][0] and t("plugins.cluster_commands_warning") in messages[-1][0]
    choose("2.0.0")
    assert c["switch_version"].IsEnabled()
    assert c["switch_version"].GetLabel() == t("plugins.activate")
    click("switch_version")
    assert read_active_versions(root)[pid] == "1.0.0" and not state["in_flight"]
    answer[0] = wx.YES
    with patch("hpc_gui.wx_plugins.activate_version", activate):
        click("switch_version")
        pump()
    assert read_active_versions(root)[pid] == "2.0.0"
    assert model.cards[0].active_version == "2.0.0"
    select()
    choose("1.0.0")
    assert c["switch_version"].GetLabel() == t("plugins.rollback")
    with patch("hpc_gui.wx_plugins.activate_version", activate):
        click("switch_version")
        pump()
    assert model.cards[0].active_version == "1.0.0"
    select()
    click("disable")
    pump()
    assert not model.cards[0].enabled
    select()
    click("disable")
    pump()
    assert model.cards[0].enabled
    select()
    answer[0] = wx.NO
    click("remove")
    assert model.cards[0].installed and not state["in_flight"]
    answer[0] = wx.YES
    click("remove")
    pump()
    assert not model.cards[0].installed
    assert listing.GetItemCount() == 0
    opened = []
    with patch.object(wx, "LaunchDefaultBrowser", lambda url: opened.append(url) or True):
        click("request")
    assert opened == [PLUGIN_REQUEST_URL]
assert not any(m.split(".")[0] in {"PySide6","PyQt5","PyQt6","shiboken6"} for m in sys.modules)
frame.Destroy()
app.ProcessPendingEvents()
"""
    env = dict(os.environ, HPC_GUI_CONFIG_ROOT=str(tmp_path))
    env["PYTHONPATH"] = os.pathsep.join([str(root / "src"), env.get("PYTHONPATH", "")])
    result = subprocess.run([sys.executable, "-u", "-X", "faulthandler", "-c", script, str(tmp_path)],
                            cwd=root, env=env, capture_output=True, text=True, timeout=45)
    assert result.returncode == 0, result.stdout + result.stderr

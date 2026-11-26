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
from pathlib import Path
import wx
from unittest.mock import patch
from hpc_gui.core.i18n import load_language, t
from hpc_gui.plugins.storage import read_active_versions, plugin_package_dir
from test_plugin_integrity import install
from hpc_gui.services.plugin_request import PLUGIN_REQUEST_URL
from hpc_gui.wx_plugins import WxPluginManagerModel
from hpc_gui.wx_plugins_view import build_plugins_panel

load_language("en")
app = wx.App(False)
app.SetExitOnFrameDelete(False)
frame = wx.Frame(None)
changed = []
frame._wx_rebuild_plugins_menu = lambda: changed.append(True)
root = sys.argv[1]
pid = "org.hpcclient.truba"
install(Path(root), version="2.0.0")
install(Path(root), version="1.0.0")
install(Path(root), version="3.0.0")
from hpc_gui.plugins.state import activate_version
activate_version(pid, "1.0.0", root=root)
corrupt = plugin_package_dir(pid, "3.0.0", root) / "cluster-profile.json"
corrupt.write_text("tampered", encoding="utf-8")
model = WxPluginManagerModel(root=root, app_version="2.0.0")
model.build_cards_from_registry({"plugins":[
    {"id":pid,"name":"Example","version":v,"requires_app":">=1.0.0",
     "type":"cluster-profile","publisher":"Example","description":"Test"}
    for v in ("1.0.0","2.0.0","3.0.0")]}, "cache")
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

with patch.object(wx, "MessageBox", message):
    select()
    assert c["versions"].GetItems() == ["3.0.0","2.0.0","1.0.0"]
    click("details")
    assert "Example" in messages[-1][0] and t("plugins.cluster_commands_warning") in messages[-1][0]
    choose("2.0.0")
    assert c["switch_version"].IsEnabled()
    assert c["switch_version"].GetLabel() == t("plugins.activate")
    click("switch_version")
    assert read_active_versions(root)[pid] == "1.0.0" and not state["in_flight"]
    answer[0] = wx.YES
    click("switch_version")
    pump()
    assert read_active_versions(root)[pid] == "2.0.0"
    assert model.cards[0].active_version == "2.0.0"
    select()
    choose("3.0.0")
    click("switch_version")
    pump()
    assert model.cards[0].active_version == "2.0.0"
    assert t("plugins.version_switch_failed").format(name="Example", version="3.0.0") in messages[-1][0]
    assert corrupt.exists()
    select()
    choose("1.0.0")
    assert c["switch_version"].GetLabel() == t("plugins.rollback")
    click("switch_version")
    pump()
    assert model.cards[0].active_version == "1.0.0"
    payload = plugin_package_dir(pid, "1.0.0", root) / "cluster-profile.json"
    original = payload.read_bytes()
    payload.write_text("corrupt", encoding="utf-8")
    model.reload_installed()
    view = c["view"]
    event = wx.CommandEvent(wx.EVT_CHOICE.typeId, view.GetId())
    event.SetEventObject(view)
    view.GetEventHandler().ProcessEvent(event)
    assert c["problems"].IsShown() and "integrity check failed" in c["problems"].GetValue()
    assert model.cards[0].problem
    payload.write_bytes(original)
    model.reload_installed()
    view.GetEventHandler().ProcessEvent(event)
    assert not c["problems"].IsShown()
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
    assert changed == [True] * 5  # activate, rollback, disable, enable, remove; no failed/cancelled action
assert not any(m.split(".")[0] in {"PySide6","PyQt5","PyQt6","shiboken6"} for m in sys.modules)
frame.Destroy()
app.ProcessPendingEvents()
"""
    env = dict(os.environ, HPC_GUI_CONFIG_ROOT=str(tmp_path))
    env["PYTHONPATH"] = os.pathsep.join([str(root / "src"), str(root / "tests"), env.get("PYTHONPATH", "")])
    result = subprocess.run([sys.executable, "-u", "-X", "faulthandler", "-c", script, str(tmp_path)],
                            cwd=root, env=env, capture_output=True, text=True, timeout=45)
    assert result.returncode == 0, result.stdout + result.stderr

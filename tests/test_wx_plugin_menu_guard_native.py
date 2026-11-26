"""Native plugin contribution events cannot bypass disabled/stale conditions."""
import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.subprocess
def test_native_plugin_menu_context_and_stale_dispatch(tmp_path):
    root = Path(__file__).resolve().parents[1]
    script = r"""
import wx
from types import SimpleNamespace as NS
from unittest.mock import patch
from hpc_gui.core.i18n import load_language
from hpc_gui.plugins.ui_contributions import PluginMenuAction, PluginMenuSubmenu, PluginMenuContribution
from hpc_gui.wx_shell_plugins import bind_plugin_menu

load_language("en")
app = wx.App(False)
app.SetExitOnFrameDelete(False)
frame = wx.Frame(None)
notebook = wx.Notebook(frame)
editor = wx.Panel(notebook)
files = wx.Panel(notebook)
listing = wx.ListCtrl(files, style=wx.LC_REPORT)
listing.InsertColumn(0, "File")
listing.InsertItem(0, "job.slurm")
local = NS(_wx_local_controls={"listing":listing})
notebook.AddPage(editor, "Editor")
notebook.AddPage(files, "Files")
pages = {"NAV-EDITOR":{"page":editor}, "NAV-FILES":{"page":files, "local":local}}
menu = wx.Menu()
menu.Append(wx.ID_ANY, "Browse")
menu.Append(wx.ID_ANY, "Manage")
updates = menu.Append(wx.ID_ANY, "Updates")
bottom = menu.AppendSeparator()
menu.Append(wx.ID_ANY, "Request")
bar = wx.MenuBar()
bar.Append(menu, "Plugins")
frame.SetMenuBar(bar)
pid = "org.example.tool"
manifest = NS(id=pid, version="1.0.0", capabilities=("lint-rules",))
plugin = NS(manifest=manifest)
actions = (
    PluginMenuAction("lint", "Selected file", {}, "editor.lint_current", {"file_selected":True}, "disable"),
    PluginMenuSubmenu("sub", "Connected", {}, (
        PluginMenuAction("child", "Child", {}, "editor.lint_current", {}, "disable", 1),
    ), {"connected":True}, "disable"),
    PluginMenuAction("ed", "Editor only", {}, "editor.lint_current", {"editor_active":True}, "hide"),
)
contrib = PluginMenuContribution(pid, "1.0.0", "Test", {}, actions)
state = {"session":None}
calls = []
errors = []
def items():
    root = next(x.GetSubMenu() for x in menu.GetMenuItems() if x.GetSubMenu())
    return {x.GetItemLabelText():x for x in root.GetMenuItems()}
def send(item):
    event = wx.CommandEvent(wx.EVT_MENU.typeId, item.GetId())
    frame.GetEventHandler().ProcessEvent(event)
with patch("hpc_gui.plugins.loader.load_installed_plugins", return_value=NS(plugins=[plugin])),      patch("hpc_gui.plugins.ui_contributions.collect_plugin_menu_contributions", return_value=[contrib]),      patch("hpc_gui.services.plugin_menu_actions.dispatch_plugin_menu_action",
           lambda action, plugin, host: calls.append((action, plugin.manifest.version)) or True),      patch("hpc_gui.wx_shell_plugins.report_wx_action_error", lambda *a, **kw: errors.append(kw)):
    frame.Show()
    bind_plugin_menu(wx, frame, state, notebook, pages, menu, bottom, updates, editor, lambda *_: None)
    a = items()
    assert "Editor only" in a and not a["Selected file"].IsEnabled()
    child = a["Connected"].GetSubMenu().GetMenuItems()[0]
    assert not child.IsEnabled()
    send(child)
    send(a["Selected file"])
    assert calls == []
    notebook.SetSelection(1)
    listing.Select(0)
    wx.Yield()
    frame._wx_rebuild_plugins_menu()
    a = items()
    assert "Editor only" not in a and a["Selected file"].IsEnabled()
    send(a["Selected file"])
    assert len(calls) == 1
    listing.Select(0, False)
    send(a["Selected file"])
    assert len(calls) == 1
    listing.Select(0)
    manifest.version = "2.0.0"
    send(a["Selected file"])
    assert len(calls) == 1 and len(errors) == 1
frame.Destroy()
app.ProcessPendingEvents()
"""
    env = dict(os.environ, HPC_GUI_CONFIG_ROOT=str(tmp_path))
    env["PYTHONPATH"] = os.pathsep.join([str(root / "src"), env.get("PYTHONPATH", "")])
    result = subprocess.run([sys.executable, "-u", "-X", "faulthandler", "-c", script],
                            cwd=root, env=env, capture_output=True, text=True, timeout=35)
    assert result.returncode == 0, result.stdout + result.stderr
